"""CLI-Skript: erzeugt eine vollständige Systemsicherung (Prompt 35).

Verwendung (z. B. per Windows-Aufgabenplanung nächtlich aufgerufen - es
gibt bewusst KEINEN eingebauten Scheduler, konsistent mit der
Ein-Prozess-Architektur des Projekts):

    python scripts/create_backup.py --output-dir backups/

Erzeugt ein ZIP mit einem konsistenten Datenbank-Snapshot + allen
Dokumentenspeicher-Verzeichnissen. WICHTIG: das Archiv enthält
vollständige, unpseudonymisierte Mandanteninhalte - wie die
Produktionsdatenbank selbst zu behandeln (verschlüsselt aufbewahren,
Zugriff beschränken).
"""

from __future__ import annotations

import argparse
import sys

from app.backup import BackupError, BackupService
from app.config import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="backups",
        help="Zielverzeichnis für das Backup-Archiv (Standard: backups/)",
    )
    args = parser.parse_args()

    settings = get_settings()
    service = BackupService(
        database_url=settings.database_url,
        intake_storage_dir=settings.intake_storage_dir,
        mail_attachment_storage_dir=settings.mail_attachment_storage_dir,
    )

    try:
        archive_path = service.create_backup(args.output_dir)
    except BackupError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"Backup erstellt: {archive_path} ({size_mb:.1f} MB)")
    print(
        "WICHTIG: Enthält vollständige, unpseudonymisierte Mandanteninhalte - "
        "verschlüsselt und zugriffsbeschränkt aufbewahren."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
