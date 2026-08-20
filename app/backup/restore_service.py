"""RestoreService – Wiederherstellung aus einem BackupService-Archiv
(Schritt 3, Teil 2).

WICHTIGE ARCHITEKTURENTSCHEIDUNG: Die Wiederherstellung ist bewusst
AUSSCHLIESSLICH über ein Offline-CLI-Kommando erreichbar
(`scripts/restore_backup.py`, `run.py restore`), NICHT über einen Button
im laufenden Dashboard. Ein "Restore"-Klick im laufenden Webserver würde
die SQLite-Datei überschreiben, während derselbe Prozess noch offene
Datenbankverbindungen/-Sessions auf die alte Datei hält - das Risiko einer
stillen Inkonsistenz oder eines Absturzes mitten im Request ist real und
unnötig, wenn eine sichere Offline-Alternative existiert (identisches
Muster zu `run.py migrate`/`create-admin`, die ebenfalls nicht über das
Dashboard, sondern als eigener Prozessaufruf laufen). Die Anwendung MUSS
vor der Wiederherstellung gestoppt sein - das CLI-Skript weist darauf
ausdrücklich hin.

Sicherheitsnetz: vor dem Überschreiben wird die AKTUELLE Datenbankdatei
(falls vorhanden) an denselben Ort mit einem Zeitstempel-Suffix kopiert
(`*.pre-restore-<Zeitstempel>.bak`) - eine fehlerhafte Wiederherstellung
lässt sich damit von Hand rückgängig machen, ohne dass der vorige Stand
unwiederbringlich verloren ist."""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class RestoreError(Exception):
    pass


@dataclass(frozen=True)
class RestoreResult:
    database_restored: bool
    intake_files_restored: int
    mail_attachment_files_restored: int
    pre_restore_database_backup: Path | None


class RestoreService:
    def __init__(
        self,
        *,
        database_url: str,
        intake_storage_dir: str,
        mail_attachment_storage_dir: str,
    ) -> None:
        self.database_url = database_url
        self.intake_storage_dir = Path(intake_storage_dir)
        self.mail_attachment_storage_dir = Path(mail_attachment_storage_dir)

    def _sqlite_db_path(self) -> Path:
        if not self.database_url.startswith("sqlite:///"):
            raise RestoreError(
                "Wiederherstellung wird aktuell nur für SQLite unterstützt "
                f"(database_url={self.database_url!r})"
            )
        return Path(self.database_url.removeprefix("sqlite:///"))

    def _validate_archive(self, archive_path: Path) -> None:
        if not archive_path.exists():
            raise RestoreError(f"Archiv nicht gefunden: {archive_path}")
        try:
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
        except zipfile.BadZipFile as exc:
            raise RestoreError(f"Kein gültiges ZIP-Archiv: {archive_path}") from exc
        if "database.db" not in names:
            raise RestoreError(
                "Archiv enthält keine 'database.db' - kein gültiges "
                "Kanzlei-AI-Backup (siehe app/backup/service.py)."
            )

    def restore_from_backup(self, archive_path: str | Path, *, confirm: bool) -> RestoreResult:
        """Überschreibt die aktuelle Datenbank UND die Dokumentenspeicher-
        Verzeichnisse mit dem Inhalt des Archivs. `confirm=True` ist
        PFLICHT - eine bewusste Sicherheitsmaßnahme gegen einen versehentlich
        aufgerufenen Restore (z. B. aus einem Skript, das die Methode ohne
        expliziten Aufrufer-Willen erreicht)."""
        if not confirm:
            raise RestoreError(
                "Wiederherstellung erfordert confirm=True - "
                "kein versehentliches Überschreiben ohne explizite Bestätigung."
            )

        archive_path = Path(archive_path)
        self._validate_archive(archive_path)
        db_path = self._sqlite_db_path()

        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(tmp_dir)

            pre_restore_backup: Path | None = None
            if db_path.exists():
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                pre_restore_backup = db_path.with_name(
                    f"{db_path.name}.pre-restore-{timestamp}.bak"
                )
                shutil.copy2(db_path, pre_restore_backup)

            db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tmp_dir / "database.db", db_path)

            intake_count = self._restore_directory(tmp_dir / "intake", self.intake_storage_dir)
            mail_count = self._restore_directory(
                tmp_dir / "mail_attachments", self.mail_attachment_storage_dir
            )

        return RestoreResult(
            database_restored=True,
            intake_files_restored=intake_count,
            mail_attachment_files_restored=mail_count,
            pre_restore_database_backup=pre_restore_backup,
        )

    def _restore_directory(self, source: Path, target: Path) -> int:
        """Kopiert (überschreibt bei Namensgleichheit, löscht aber keine
        Dateien, die im Archiv nicht vorkommen - additive Wiederherstellung,
        kein `rm -rf` des Zielordners)."""
        if not source.exists():
            return 0
        target.mkdir(parents=True, exist_ok=True)
        count = 0
        for file_path in source.rglob("*"):
            if file_path.is_file():
                relative = file_path.relative_to(source)
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, destination)
                count += 1
        return count
