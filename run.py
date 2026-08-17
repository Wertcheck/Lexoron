"""Windows-Entry-Point für die gebündelte Anwendung (Prompt 36/37).

Dies ist die einzige Datei, die PyInstaller bündelt (siehe
windows/kanzlei_ai.spec) - ein dünner Dispatcher, keine Fachlogik. Bietet
vier Subkommandos:

    kanzlei_ai.exe serve          (Standard, auch ohne Argument) - startet
                                   den Webserver. Führt vorher automatisch
                                   ausstehende Datenbankmigrationen aus
                                   ("bei jedem Update", siehe HANDOFF-Doku)
                                   und stößt bei fehlender Konfiguration
                                   automatisch den Setup-Assistenten an.
    kanzlei_ai.exe setup          - Ersteinrichtung: Datenverzeichnis,
                                   `.env` (inkl. generiertem
                                   SESSION_SECRET_KEY), Migration, Admin.
    kanzlei_ai.exe migrate        - führt nur `alembic upgrade head` aus.
    kanzlei_ai.exe create-admin   - ruft scripts/create_admin.py auf
                                   (liest ADMIN_EMAIL/ADMIN_INITIAL_PASSWORD
                                   aus der Prozessumgebung).

WICHTIG zur Prozessarchitektur: `setup` ruft `migrate`/`create-admin` NICHT
direkt als Python-Funktionsaufruf im selben Prozess auf, sondern startet
sich selbst als NEUEN Subprozess (`_self_command`). Grund: `app.config.
get_settings()` ist `@lru_cache`d und `app/db/session.py` erzeugt die
SQLAlchemy-Engine bereits beim Modul-Import - beides liest die Konfiguration
also spätestens beim ERSTEN Import im laufenden Prozess. Da `setup` selbst
die `.env`-Datei erst währenddessen schreibt, muss jeder nachfolgende
Schritt in einem GARANTIERT frischen Prozess laufen, der die neue `.env`
von Anfang an sieht - alles andere wäre eine fragile Abhängigkeit von der
Importreihenfolge. Siehe auch app/setup/wizard.py (dort ausführlicher
begründet, dort injiziert statt hier fest verdrahtet - macht die eigentliche
Ablauflogik ohne Subprozesse testbar).

Vor JEDEM Subkommando wechselt dieser Entry-Point in das persistente
Datenverzeichnis (siehe app/setup/paths.py), unabhängig davon, wie/von wo
die .exe gestartet wurde (Startmenü-Verknüpfung mit gesetztem Arbeits-
verzeichnis, Doppelklick im Installationsordner, Windows-Aufgabenplanung).
Das ist der einzige Mechanismus, der sicherstellt, dass relative Pfade in
den Settings (DATABASE_URL, INTAKE_STORAGE_DIR, ...) IMMER im
Datenverzeichnis landen, nie versehentlich im schreibgeschützten
Installationsordner.
"""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path


def _bundle_base_dir() -> Path:
    """Verzeichnis mit `alembic.ini`/`migrations/` - im Dev-Betrieb das
    Repository-Root (diese Datei liegt dort), in der gebündelten .exe das
    von PyInstaller bereitgestellte Bundle-Verzeichnis (siehe
    windows/kanzlei_ai.spec, `datas`-Eintrag für beide)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


def _self_command(*extra_args: str) -> list[str]:
    """Kommandozeile, um DIESES Programm (dev: `python run.py ...`,
    gebündelt: `kanzlei_ai.exe ...`) als neuen Subprozess zu starten."""
    if getattr(sys, "frozen", False):
        return [sys.executable, *extra_args]
    return [sys.executable, str(Path(__file__).resolve()), *extra_args]


def cmd_migrate() -> int:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(_bundle_base_dir() / "alembic.ini"))
    command.upgrade(cfg, "head")
    return 0


def cmd_create_admin() -> int:
    from scripts.create_admin import main as create_admin_main

    return create_admin_main()


def cmd_serve() -> int:
    from app.config import get_settings

    settings = get_settings()

    # Ausstehende Migrationen automatisch anwenden - laut Handoff-Doku
    # "muss beim ersten Start (und bei jedem Update) laufen". Alembic-
    # Upgrades sind idempotent (kein Effekt, wenn bereits auf "head").
    migrate_exit_code = cmd_migrate()
    if migrate_exit_code != 0:
        return migrate_exit_code

    import uvicorn

    from app.main import app

    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level.lower())
    return 0


def _run_migrate_subprocess(data_dir: Path) -> None:
    result = subprocess.run(_self_command("migrate"), cwd=str(data_dir), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Datenbankmigration fehlgeschlagen (Exit-Code {result.returncode}).")


def _run_create_admin_subprocess(data_dir: Path, email: str, password: str | None) -> None:
    env = dict(os.environ)
    env["ADMIN_EMAIL"] = email
    if password:
        env["ADMIN_INITIAL_PASSWORD"] = password
    else:
        env.pop("ADMIN_INITIAL_PASSWORD", None)
    result = subprocess.run(_self_command("create-admin"), cwd=str(data_dir), env=env, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Anlegen des Admin-Nutzers fehlgeschlagen (Exit-Code {result.returncode}).")


def cmd_setup(data_dir: Path, *, force: bool) -> int:
    from app.config.settings import Settings
    from app.setup import WizardError, run_setup_wizard

    print("=== Kanzlei-AI Setup-Assistent ===")
    print(f"Datenverzeichnis: {data_dir}")
    admin_email = input("E-Mail-Adresse des ersten Admin-Nutzers: ").strip()
    entered_password = getpass.getpass(
        "Initiales Admin-Passwort (leer lassen, um automatisch eines zu generieren): "
    )
    admin_password = entered_password or None

    default_host = Settings.model_fields["host"].default
    default_port = Settings.model_fields["port"].default

    try:
        result = run_setup_wizard(
            data_dir=data_dir,
            admin_email=admin_email,
            admin_password=admin_password,
            run_migrations=lambda: _run_migrate_subprocess(data_dir),
            create_admin=lambda email, password: _run_create_admin_subprocess(
                data_dir, email, password
            ),
            host=default_host,
            port=default_port,
            force=force,
        )
    except (WizardError, FileExistsError, RuntimeError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1

    print(f"Setup abgeschlossen. Konfiguration geschrieben nach: {result.env_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    parser = argparse.ArgumentParser(prog="kanzlei_ai", description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("serve", help="Startet den Webserver (Standard ohne Argument)")
    setup_parser = subparsers.add_parser("setup", help="Führt die Ersteinrichtung durch")
    setup_parser.add_argument(
        "--force",
        action="store_true",
        help="Bestehende .env überschreiben (Vorsicht: macht laufende Sessions ungültig)",
    )
    subparsers.add_parser("migrate", help="Führt ausstehende Datenbankmigrationen aus")
    subparsers.add_parser(
        "create-admin",
        help="Legt den initialen Admin-Nutzer an (liest ADMIN_EMAIL/ADMIN_INITIAL_PASSWORD)",
    )

    args = parser.parse_args(argv)
    command = args.command or "serve"

    from app.setup import resolve_data_dir

    data_dir = resolve_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(data_dir)

    if command == "setup":
        return cmd_setup(data_dir, force=args.force)
    if command == "migrate":
        return cmd_migrate()
    if command == "create-admin":
        return cmd_create_admin()

    # command == "serve"
    env_path = data_dir / ".env"
    if not env_path.exists():
        print("Keine Konfiguration gefunden - Ersteinrichtung wird gestartet.")
        setup_exit_code = cmd_setup(data_dir, force=False)
        if setup_exit_code != 0:
            return setup_exit_code
    return cmd_serve()


if __name__ == "__main__":
    raise SystemExit(main())
