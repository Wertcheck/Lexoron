"""Tests fuer app/ingestion/intake.py (Prompt 05).

Nutzt ausschliesslich synthetische Testdateien in tmp_path - keine echten
Mandantendaten. Eigene In-Memory-SQLite-DB (analog zu test_models.py).
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ingestion.intake import IntakeError, IntakeService
from app.ingestion.stability import compute_sha256
from app.models import AuditEvent, Document
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


def _make_source_file(tmp_path: Path, name: str = "eingang.pdf") -> Path:
    source_dir = tmp_path / "eingang_ordner"
    source_dir.mkdir(exist_ok=True)
    source_path = source_dir / name
    source_path.write_bytes(b"Synthetischer Testinhalt - kein echtes Dokument")
    return source_path


def test_ingest_file_copies_file_and_creates_document(
    tmp_path: Path, db_session: Session
) -> None:
    source_path = _make_source_file(tmp_path)
    storage_dir = tmp_path / "intake_storage"
    service = IntakeService(storage_dir)

    document = service.ingest_file(source_path, db_session)

    assert isinstance(document, Document)
    assert document.id is not None
    assert document.original_filename == "eingang.pdf"
    assert document.mime_type == "application/pdf"
    assert document.content_hash == compute_sha256(source_path)

    destination_path = Path(document.file_path)
    assert destination_path.exists()
    assert destination_path.parent == storage_dir
    assert destination_path.read_bytes() == source_path.read_bytes()

    # Original bleibt unangetastet (kopiert, nicht verschoben).
    assert source_path.exists()


def test_ingest_file_does_not_overwrite_original(
    tmp_path: Path, db_session: Session
) -> None:
    source_path = _make_source_file(tmp_path)
    original_bytes = source_path.read_bytes()
    service = IntakeService(tmp_path / "intake_storage")

    service.ingest_file(source_path, db_session)

    assert source_path.read_bytes() == original_bytes


def test_ingest_file_handles_duplicate_filenames_without_collision(
    tmp_path: Path, db_session: Session
) -> None:
    """Zwei unterschiedliche Quelldateien mit gleichem Namen (z. B. aus
    verschiedenen Unterordnern) duerfen sich im Intake-Bereich nicht
    gegenseitig ueberschreiben."""
    storage_dir = tmp_path / "intake_storage"
    service = IntakeService(storage_dir)

    source_1_dir = tmp_path / "ordner_a"
    source_1_dir.mkdir()
    source_1 = source_1_dir / "schreiben.pdf"
    source_1.write_bytes(b"Inhalt A")

    source_2_dir = tmp_path / "ordner_b"
    source_2_dir.mkdir()
    source_2 = source_2_dir / "schreiben.pdf"
    source_2.write_bytes(b"Inhalt B")

    doc_1 = service.ingest_file(source_1, db_session)
    doc_2 = service.ingest_file(source_2, db_session)

    assert doc_1.file_path != doc_2.file_path
    assert Path(doc_1.file_path).read_bytes() == b"Inhalt A"
    assert Path(doc_2.file_path).read_bytes() == b"Inhalt B"


def test_ingest_file_creates_audit_event(tmp_path: Path, db_session: Session) -> None:
    source_path = _make_source_file(tmp_path)
    service = IntakeService(tmp_path / "intake_storage")

    document = service.ingest_file(source_path, db_session)

    audit_events = db_session.query(AuditEvent).filter_by(entity_id=document.id).all()
    assert len(audit_events) == 1
    assert audit_events[0].entity_type == "Document"
    assert audit_events[0].event_type == "intake_created"
    assert audit_events[0].actor == "system"


def test_ingest_file_raises_for_missing_source(
    tmp_path: Path, db_session: Session
) -> None:
    missing_path = tmp_path / "existiert_nicht.pdf"
    service = IntakeService(tmp_path / "intake_storage")

    with pytest.raises(IntakeError):
        service.ingest_file(
            missing_path, db_session, stability_timeout_seconds=0.3
        )

    # Bei Fehler darf kein Document-Eintrag entstehen.
    assert db_session.query(Document).count() == 0


def test_ingest_file_document_has_no_matter_assigned_yet(
    tmp_path: Path, db_session: Session
) -> None:
    """Aktenzuordnung ist nicht Teil von Prompt 05 (folgt in Prompt 09)."""
    source_path = _make_source_file(tmp_path)
    service = IntakeService(tmp_path / "intake_storage")

    document = service.ingest_file(source_path, db_session)

    assert document.matter_id is None
