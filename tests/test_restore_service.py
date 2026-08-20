"""Tests für app/backup/restore_service.py (Schritt 3, Teil 2)."""

from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path

import pytest

from app.backup import BackupService, RestoreError, RestoreService


def _make_backup(tmp_path: Path) -> Path:
    db_path = tmp_path / "source" / "kanzlei_ai.db"
    db_path.parent.mkdir(parents=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE t (id INTEGER)")
    conn.execute("INSERT INTO t VALUES (42)")
    conn.commit()
    conn.close()

    intake_dir = tmp_path / "source" / "intake"
    intake_dir.mkdir()
    (intake_dir / "dokument.pdf").write_text("Original-Dokumentinhalt")

    mail_dir = tmp_path / "source" / "mail_attachments"
    mail_dir.mkdir()
    (mail_dir / "anhang.pdf").write_text("Original-Anhang")

    service = BackupService(
        database_url=f"sqlite:///{db_path}",
        intake_storage_dir=str(intake_dir),
        mail_attachment_storage_dir=str(mail_dir),
    )
    return service.create_backup(tmp_path / "backups")


def test_restore_requires_explicit_confirmation(tmp_path: Path) -> None:
    archive = _make_backup(tmp_path)
    target_db = tmp_path / "target" / "kanzlei_ai.db"
    service = RestoreService(
        database_url=f"sqlite:///{target_db}",
        intake_storage_dir=str(tmp_path / "target" / "intake"),
        mail_attachment_storage_dir=str(tmp_path / "target" / "mail_attachments"),
    )

    with pytest.raises(RestoreError):
        service.restore_from_backup(archive, confirm=False)
    assert not target_db.exists()


def test_restore_rejects_invalid_archive(tmp_path: Path) -> None:
    bogus = tmp_path / "not_a_backup.zip"
    with zipfile.ZipFile(bogus, "w") as archive:
        archive.writestr("irrelevant.txt", "kein Backup")

    service = RestoreService(
        database_url=f"sqlite:///{tmp_path / 'target.db'}",
        intake_storage_dir=str(tmp_path / "intake"),
        mail_attachment_storage_dir=str(tmp_path / "mail_attachments"),
    )
    with pytest.raises(RestoreError):
        service.restore_from_backup(bogus, confirm=True)


def test_restore_rejects_missing_archive(tmp_path: Path) -> None:
    service = RestoreService(
        database_url=f"sqlite:///{tmp_path / 'target.db'}",
        intake_storage_dir=str(tmp_path / "intake"),
        mail_attachment_storage_dir=str(tmp_path / "mail_attachments"),
    )
    with pytest.raises(RestoreError):
        service.restore_from_backup(tmp_path / "does_not_exist.zip", confirm=True)


def test_restore_writes_database_and_directories(tmp_path: Path) -> None:
    archive = _make_backup(tmp_path)
    target_db = tmp_path / "target" / "kanzlei_ai.db"
    target_intake = tmp_path / "target" / "intake"
    target_mail = tmp_path / "target" / "mail_attachments"

    service = RestoreService(
        database_url=f"sqlite:///{target_db}",
        intake_storage_dir=str(target_intake),
        mail_attachment_storage_dir=str(target_mail),
    )
    result = service.restore_from_backup(archive, confirm=True)

    assert result.database_restored is True
    assert result.intake_files_restored == 1
    assert result.mail_attachment_files_restored == 1
    assert (target_intake / "dokument.pdf").read_text() == "Original-Dokumentinhalt"
    assert (target_mail / "anhang.pdf").read_text() == "Original-Anhang"

    conn = sqlite3.connect(str(target_db))
    assert conn.execute("SELECT id FROM t").fetchone() == (42,)
    conn.close()


def test_restore_creates_safety_backup_of_existing_database(tmp_path: Path) -> None:
    archive = _make_backup(tmp_path)
    target_db = tmp_path / "target" / "kanzlei_ai.db"
    target_db.parent.mkdir(parents=True)
    target_db.write_text("ALTER BESTAND - MUSS ERHALTEN BLEIBEN")

    service = RestoreService(
        database_url=f"sqlite:///{target_db}",
        intake_storage_dir=str(tmp_path / "target" / "intake"),
        mail_attachment_storage_dir=str(tmp_path / "target" / "mail_attachments"),
    )
    result = service.restore_from_backup(archive, confirm=True)

    assert result.pre_restore_database_backup is not None
    assert result.pre_restore_database_backup.exists()
    assert (
        result.pre_restore_database_backup.read_text()
        == "ALTER BESTAND - MUSS ERHALTEN BLEIBEN"
    )
    # Zielpfad enthaelt jetzt den wiederhergestellten Stand, nicht mehr den alten.
    assert target_db.read_text() != "ALTER BESTAND - MUSS ERHALTEN BLEIBEN"


def test_restore_does_not_delete_files_absent_from_archive(tmp_path: Path) -> None:
    """Additive Wiederherstellung: eine bestehende Datei im Zielordner, die
    NICHT im Archiv vorkommt, bleibt erhalten (kein rm -rf des Zielordners)."""
    archive = _make_backup(tmp_path)
    target_intake = tmp_path / "target" / "intake"
    target_intake.mkdir(parents=True)
    (target_intake / "nur_lokal_vorhanden.pdf").write_text("bleibt erhalten")

    service = RestoreService(
        database_url=f"sqlite:///{tmp_path / 'target' / 'kanzlei_ai.db'}",
        intake_storage_dir=str(target_intake),
        mail_attachment_storage_dir=str(tmp_path / "target" / "mail_attachments"),
    )
    service.restore_from_backup(archive, confirm=True)

    assert (target_intake / "nur_lokal_vorhanden.pdf").exists()
    assert (target_intake / "dokument.pdf").exists()
