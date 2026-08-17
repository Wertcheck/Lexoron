"""Reine Erzeugung/Schreiblogik der Produktions-`.env`-Datei (Prompt 37).

`build_env_content` ist bewusst eine reine Funktion (kein Dateizugriff) -
so lässt sich der erzeugte Inhalt ohne Dateisystem-Fixtures prüfen.
`write_env_file` ist der einzige Ort, der tatsächlich schreibt, und bewusst
NICHT überschreibend per Default (analog zu `scripts/create_admin.py`, das
ebenfalls idempotent ist und einen bestehenden Admin nicht stillschweigend
überschreibt).
"""

from __future__ import annotations

from pathlib import Path


def build_env_content(
    *,
    data_dir: Path,
    session_secret: str,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> str:
    """Erzeugt den vollständigen Inhalt der Produktions-`.env`-Datei.

    Alle Pfade liegen unterhalb von `data_dir` (siehe `paths.resolve_data_dir`)
    - bewusst NICHT im Installationsverzeichnis, siehe ARCHITECTURE.md.
    Pfadwerte werden in doppelte Anführungszeichen gesetzt, falls der vom
    Betriebssystem gelieferte Datenverzeichnis-Pfad Leerzeichen enthält
    (z. B. ein individuell gewähltes `KANZLEI_AI_DATA_DIR`).
    """
    data_dir_posix = data_dir.as_posix()
    database_path = f"{data_dir_posix}/data/kanzlei_ai.db"
    intake_dir = f"{data_dir_posix}/data/intake"
    mail_attachment_dir = f"{data_dir_posix}/data/mail_attachments"
    log_file_path = f"{data_dir_posix}/logs/kanzlei_ai.log"

    return (
        "# Automatisch erzeugt vom Setup-Assistenten (app/setup/wizard.py, Prompt 37).\n"
        "# NIEMALS von Hand editieren, ohne die Auswirkungen auf SESSION_SECRET_KEY\n"
        "# (aktive Sessions werden bei Aenderung ungueltig) und die Pfade unten zu kennen.\n"
        "\n"
        "APP_ENV=production\n"
        "\n"
        f'DATABASE_URL="sqlite:///{database_path}"\n'
        f'INTAKE_STORAGE_DIR="{intake_dir}"\n'
        f'MAIL_ATTACHMENT_STORAGE_DIR="{mail_attachment_dir}"\n'
        f'LOG_FILE_PATH="{log_file_path}"\n'
        "\n"
        f"SESSION_SECRET_KEY={session_secret}\n"
        "SESSION_COOKIE_SECURE=True\n"
        "\n"
        f"HOST={host}\n"
        f"PORT={port}\n"
    )


def write_env_file(target_path: Path, content: str, *, force: bool = False) -> None:
    """Schreibt `content` nach `target_path`.

    Verweigert das Überschreiben einer bereits bestehenden Konfiguration
    ohne `force=True` - eine bestehende `.env` enthält u. a. den aktiven
    `SESSION_SECRET_KEY`; ein unbeabsichtigtes Überschreiben würde alle
    laufenden Sessions ungültig machen und könnte eine bereits laufende
    Installation durcheinanderbringen.
    """
    if target_path.exists() and not force:
        raise FileExistsError(
            f"{target_path} existiert bereits - Setup-Assistent nicht erneut ohne "
            "ausdrückliche Bestätigung (force=True) ausgeführt, um eine bestehende "
            "Konfiguration (inkl. aktivem SESSION_SECRET_KEY) nicht zu überschreiben."
        )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
