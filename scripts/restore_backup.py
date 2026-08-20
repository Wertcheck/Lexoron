"""Einmaliges Wiederherstellungs-Skript für ein Backup-Archiv (Schritt 3).

WICHTIG: Die Anwendung MUSS gestoppt sein, bevor dieses Skript läuft - siehe
app/backup/restore_service.py für die Begründung (keine Live-Restore-Aktion
im laufenden Webserver). Wird manuell ausgeführt:

    python scripts/restore_backup.py --archive pfad/zum/backup.zip

Fragt interaktiv nach einer Bestätigung ("JA" eintippen), es sei denn
`--yes` wird übergeben (z. B. für ein dokumentiertes, nicht-interaktives
Notfall-Runbook). Erstellt vor dem Überschreiben automatisch eine
Sicherheitskopie der aktuellen Datenbankdatei (siehe RestoreService).
"""

from __future__ import annotations

import argparse
import sys

from app.backup import RestoreError, RestoreService
from app.config import get_settings


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    parser = argparse.ArgumentParser(
        prog="restore_backup",
        description=(
            "Stellt Datenbank und Dokumentenspeicher aus einem Lexono-"
            "Backup-Archiv wieder her. Die Anwendung MUSS dafür gestoppt sein."
        ),
    )
    parser.add_argument("--archive", required=True, help="Pfad zum Backup-ZIP")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Bestätigung überspringen (nur für dokumentierte, nicht-interaktive Abläufe)",
    )
    args = parser.parse_args(argv)

    print("=== Lexono Wiederherstellung ===")
    print(f"Archiv: {args.archive}")
    print(
        "WARNUNG: Dies überschreibt die aktuelle Datenbank und die "
        "Dokumentenspeicher-Verzeichnisse. Die Anwendung MUSS dafür gestoppt sein.\n"
        "Eine Sicherheitskopie der aktuellen Datenbank wird automatisch angelegt."
    )

    if not args.yes:
        answer = input("Fortfahren? Zum Bestätigen 'JA' eintippen: ").strip()
        if answer != "JA":
            print("Abgebrochen - keine Änderung vorgenommen.", file=sys.stderr)
            return 1

    settings = get_settings()
    service = RestoreService(
        database_url=settings.database_url,
        intake_storage_dir=settings.intake_storage_dir,
        mail_attachment_storage_dir=settings.mail_attachment_storage_dir,
    )
    try:
        result = service.restore_from_backup(args.archive, confirm=True)
    except RestoreError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1

    print("Wiederherstellung abgeschlossen.")
    if result.pre_restore_database_backup:
        print(f"Sicherheitskopie der vorherigen Datenbank: {result.pre_restore_database_backup}")
    print(f"Intake-Dateien wiederhergestellt: {result.intake_files_restored}")
    print(f"E-Mail-Anhänge wiederhergestellt: {result.mail_attachment_files_restored}")
    print("Bitte die Anwendung jetzt neu starten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
