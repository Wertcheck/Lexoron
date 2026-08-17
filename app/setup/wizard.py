"""Orchestrierung der Ersteinrichtung (Prompt 37).

Reine Ablauflogik, keine Konsolen-Interaktion (siehe app/setup/__init__.py).
Migration und Admin-Anlage werden als Callables injiziert, siehe Docstring
von `run_setup_wizard` für die Begründung (Prozessgrenzen wegen
`lru_cache`d Settings).
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .env_writer import build_env_content, write_env_file


class WizardError(Exception):
    """Fehler während des Setup-Assistenten (z. B. ungültige Eingabe)."""


@dataclass(frozen=True)
class WizardResult:
    env_path: Path
    data_dir: Path


def run_setup_wizard(
    *,
    data_dir: Path,
    admin_email: str,
    admin_password: str | None,
    run_migrations: Callable[[], None],
    create_admin: Callable[[str, str | None], None],
    host: str = "127.0.0.1",
    port: int = 8000,
    force: bool = False,
) -> WizardResult:
    """Führt die Ersteinrichtung durch: Verzeichnisse, `.env`, Migration, Admin.

    `run_migrations`/`create_admin` werden injiziert statt hier direkt
    aufgerufen: in der tatsächlichen Windows-Installation laufen beide als
    SEPARATER Prozessaufruf derselben gebündelten .exe (siehe `run.py`),
    weil `app.config.get_settings()` (`@lru_cache`) und `app.db.session`
    die Konfiguration beim ERSTEN Import im laufenden Prozess einlesen bzw.
    fest verdrahten (Engine-Erzeugung beim Modul-Import). Ein frischer
    Prozess pro Schritt stellt sicher, dass die gerade geschriebene `.env`
    tatsächlich gelesen wird, ohne Cache-Invalidierung über bereits
    importierte Module nachvollziehen zu müssen. Für Tests genügt ein
    einfacher In-Prozess-Callable (siehe tests/test_setup_wizard.py).

    Reihenfolge bewusst: Validierung → Verzeichnisse → `.env` schreiben →
    Migration → Admin-Anlage. Ein Fehler in einem späteren Schritt lässt die
    vorherigen Ergebnisse (Verzeichnisse, `.env`) bestehen - ein erneuter
    Lauf mit `force=True` kann daran anknüpfen, statt bei Null zu beginnen.
    """
    _validate_admin_email(admin_email)

    (data_dir / "data").mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)

    session_secret = secrets.token_urlsafe(48)
    content = build_env_content(
        data_dir=data_dir, session_secret=session_secret, host=host, port=port
    )
    env_path = data_dir / ".env"
    write_env_file(env_path, content, force=force)

    run_migrations()
    create_admin(admin_email, admin_password)

    return WizardResult(env_path=env_path, data_dir=data_dir)


def _validate_admin_email(email: str) -> None:
    if not email or not email.strip():
        raise WizardError("Admin-E-Mail-Adresse darf nicht leer sein.")
    if "@" not in email:
        raise WizardError(f"'{email}' sieht nicht wie eine gültige E-Mail-Adresse aus.")
