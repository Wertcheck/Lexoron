"""Tests für app/backup/ und app/export/ (Prompt 35)."""

from __future__ import annotations

import json
import sqlite3
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.backup import BackupError, BackupService
from app.export import MatterExportService, MatterNotFoundError
from app.models import AttorneyInstruction, Client, Deadline, Document, Draft, Matter, Message
from app.models.base import Base


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _make_matter(db: Session, **overrides) -> Matter:
    client = Client(name="Testmandant GmbH")
    matter = Matter(client=client, title="Testakte", reference_number="2026/0001-ESt")
    for key, value in overrides.items():
        setattr(matter, key, value)
    db.add_all([client, matter])
    db.commit()
    return matter


# ==========================================================================
# 1. BackupService
# ==========================================================================


def test_create_backup_produces_valid_zip(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE t (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO t VALUES (1, 'Testwert')")
    conn.commit()
    conn.close()

    intake_dir = tmp_path / "intake"
    intake_dir.mkdir()
    (intake_dir / "scan.pdf").write_bytes(b"Testinhalt")

    service = BackupService(
        database_url=f"sqlite:///{db_path}",
        intake_storage_dir=str(intake_dir),
        mail_attachment_storage_dir=str(tmp_path / "nicht_vorhanden"),
    )
    output_dir = tmp_path / "backups"
    archive_path = service.create_backup(output_dir)

    assert archive_path.exists()
    assert zipfile.is_zipfile(archive_path)


def test_backup_contains_consistent_database_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE t (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO t VALUES (1, 'Konsistenztest')")
    conn.commit()
    conn.close()

    service = BackupService(
        database_url=f"sqlite:///{db_path}",
        intake_storage_dir=str(tmp_path / "intake"),
        mail_attachment_storage_dir=str(tmp_path / "mail"),
    )
    archive_path = service.create_backup(tmp_path / "backups")

    with zipfile.ZipFile(archive_path) as archive:
        db_bytes = archive.read("database.db")
        restored_path = tmp_path / "restored.db"
        restored_path.write_bytes(db_bytes)
        restored_conn = sqlite3.connect(str(restored_path))
        rows = restored_conn.execute("SELECT * FROM t").fetchall()
        assert rows == [(1, "Konsistenztest")]


def test_backup_includes_document_storage_directories(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    sqlite3.connect(str(db_path)).close()

    intake_dir = tmp_path / "intake"
    intake_dir.mkdir()
    (intake_dir / "dokument.pdf").write_bytes(b"Testinhalt")

    mail_dir = tmp_path / "mail_attachments"
    mail_dir.mkdir()
    (mail_dir / "anhang.pdf").write_bytes(b"Anhang-Testinhalt")

    service = BackupService(
        database_url=f"sqlite:///{db_path}",
        intake_storage_dir=str(intake_dir),
        mail_attachment_storage_dir=str(mail_dir),
    )
    archive_path = service.create_backup(tmp_path / "backups")

    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        assert "intake/dokument.pdf" in names
        assert "mail_attachments/anhang.pdf" in names


def test_backup_includes_info_file_with_sensitivity_warning(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    sqlite3.connect(str(db_path)).close()
    service = BackupService(
        database_url=f"sqlite:///{db_path}",
        intake_storage_dir=str(tmp_path / "intake"),
        mail_attachment_storage_dir=str(tmp_path / "mail"),
    )
    archive_path = service.create_backup(tmp_path / "backups")

    with zipfile.ZipFile(archive_path) as archive:
        info_text = archive.read("BACKUP_INFO.txt").decode("utf-8")
        assert "unpseudonymisierte" in info_text


def test_backup_missing_database_raises_backup_error(tmp_path: Path) -> None:
    service = BackupService(
        database_url=f"sqlite:///{tmp_path / 'nicht_vorhanden.db'}",
        intake_storage_dir=str(tmp_path / "intake"),
        mail_attachment_storage_dir=str(tmp_path / "mail"),
    )
    with pytest.raises(BackupError):
        service.create_backup(tmp_path / "backups")


def test_backup_rejects_non_sqlite_database_url(tmp_path: Path) -> None:
    service = BackupService(
        database_url="postgresql://user:pass@localhost/db",
        intake_storage_dir=str(tmp_path / "intake"),
        mail_attachment_storage_dir=str(tmp_path / "mail"),
    )
    with pytest.raises(BackupError):
        service.create_backup(tmp_path / "backups")


def test_repeated_backups_never_overwrite_each_other(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    sqlite3.connect(str(db_path)).close()
    service = BackupService(
        database_url=f"sqlite:///{db_path}",
        intake_storage_dir=str(tmp_path / "intake"),
        mail_attachment_storage_dir=str(tmp_path / "mail"),
    )
    output_dir = tmp_path / "backups"
    first = service.create_backup(output_dir)
    import time

    time.sleep(1.1)
    second = service.create_backup(output_dir)
    assert first != second
    assert first.exists()
    assert second.exists()


# ==========================================================================
# 2. MatterExportService
# ==========================================================================


def test_export_matter_produces_valid_zip(db_session: Session, tmp_path: Path) -> None:
    matter = _make_matter(db_session)
    service = MatterExportService()
    archive_path = service.export_matter(matter.id, db_session, tmp_path)
    assert archive_path.exists()
    assert zipfile.is_zipfile(archive_path)


def test_export_matter_unknown_id_raises(db_session: Session, tmp_path: Path) -> None:
    service = MatterExportService()
    with pytest.raises(MatterNotFoundError):
        service.export_matter("nicht-vorhanden", db_session, tmp_path)


def test_export_manifest_contains_matter_and_client(
    db_session: Session, tmp_path: Path
) -> None:
    matter = _make_matter(db_session)
    service = MatterExportService()
    archive_path = service.export_matter(matter.id, db_session, tmp_path)

    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["matter"]["title"] == "Testakte"
    assert manifest["matter"]["client_name"] == "Testmandant GmbH"


def test_export_manifest_includes_all_related_records(
    db_session: Session, tmp_path: Path
) -> None:
    matter = _make_matter(db_session)
    message = Message(
        matter=matter,
        direction="inbound",
        sender="max@example-testdomain.invalid",
        body_text="Testnachricht.",
    )
    draft = Draft(matter=matter, content="Testentwurf v1.")
    db_session.add_all([message, draft])
    db_session.commit()

    draft_v2 = Draft(
        matter=matter, content="Testentwurf v2.", version=2, previous_version_id=draft.id
    )
    instruction = AttorneyInstruction(
        matter_id=matter.id,
        draft_id=draft.id,
        instruction_text="Testanmerkung.",
        actor="anwalt@kanzlei.test",
    )
    deadline = Deadline(matter_id=matter.id, source_text="Testfrist.")
    db_session.add_all([draft_v2, instruction, deadline])
    db_session.commit()

    service = MatterExportService()
    archive_path = service.export_matter(matter.id, db_session, tmp_path)

    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))

    assert len(manifest["messages"]) == 1
    assert len(manifest["drafts"]) == 2
    assert len(manifest["attorney_instructions"]) == 1
    assert len(manifest["deadlines"]) == 1


def test_export_includes_document_file_copies(db_session: Session, tmp_path: Path) -> None:
    matter = _make_matter(db_session)
    real_file = tmp_path / "original_scan.pdf"
    real_file.write_bytes(b"Testinhalt des Dokuments.")
    document = Document(
        matter=matter, original_filename="original_scan.pdf", file_path=str(real_file)
    )
    db_session.add(document)
    db_session.commit()

    service = MatterExportService()
    output_dir = tmp_path / "export_output"
    archive_path = service.export_matter(matter.id, db_session, output_dir)

    with zipfile.ZipFile(archive_path) as archive:
        matching = [n for n in archive.namelist() if n.startswith("documents/")]
        assert len(matching) == 1
        assert "original_scan.pdf" in matching[0]


def test_export_gracefully_skips_missing_document_files(
    db_session: Session, tmp_path: Path
) -> None:
    """Ein Dokument, dessen physische Datei nicht mehr existiert, darf den
    gesamten Export nicht zum Absturz bringen - wird einfach ausgelassen."""
    matter = _make_matter(db_session)
    document = Document(
        matter=matter,
        original_filename="verschwunden.pdf",
        file_path=str(tmp_path / "existiert_nicht.pdf"),
    )
    db_session.add(document)
    db_session.commit()

    service = MatterExportService()
    archive_path = service.export_matter(matter.id, db_session, tmp_path / "out")
    assert archive_path.exists()


def test_export_manifest_has_no_cross_matter_leakage(
    db_session: Session, tmp_path: Path
) -> None:
    matter_a = _make_matter(db_session)
    client_b = Client(name="Anderer Mandant")
    matter_b = Matter(client=client_b, title="Andere Akte", reference_number="2026/0002-BP")
    db_session.add_all([client_b, matter_b])
    db_session.commit()

    message_a = Message(matter=matter_a, direction="inbound", body_text="Nachricht A")
    message_b = Message(matter=matter_b, direction="inbound", body_text="Nachricht B")
    db_session.add_all([message_a, message_b])
    db_session.commit()

    service = MatterExportService()
    archive_path = service.export_matter(matter_a.id, db_session, tmp_path)

    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))

    all_bodies = [m["body_text"] for m in manifest["messages"]]
    assert "Nachricht A" in all_bodies
    assert "Nachricht B" not in all_bodies


def test_export_filename_uses_reference_number(db_session: Session, tmp_path: Path) -> None:
    matter = _make_matter(db_session, reference_number="2026/0099-USt")
    service = MatterExportService()
    archive_path = service.export_matter(matter.id, db_session, tmp_path)
    assert "2026-0099-USt" in archive_path.name
