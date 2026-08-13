"""Tests fuer app/classification/service.py (Prompt 08)."""

import json
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.classification.classifier import PlaceholderDocumentClassifier
from app.classification.service import ClassificationService
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


def _make_document(db: Session, *, extracted_text: str | None) -> Document:
    document = Document(
        file_path="/tmp/testdatei.pdf",
        original_filename="testdatei.pdf",
        extracted_text=extracted_text,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def test_classifies_document_with_text_and_persists_result(db_session: Session) -> None:
    document = _make_document(db_session, extracted_text="Anbei unsere Rechnung Nr. 42.")
    service = ClassificationService(
        PlaceholderDocumentClassifier(), low_confidence_threshold=0.6
    )

    result = service.classify_document(document, db_session)

    assert result.classified_type == "Rechnung"
    assert result.classification_confidence is not None
    assert result.classification_reasoning is not None
    assert result.classification_result_json is not None
    parsed = json.loads(result.classification_result_json)
    assert parsed["document_type"] == "Rechnung"


def test_skips_classification_when_no_extracted_text(db_session: Session) -> None:
    document = _make_document(db_session, extracted_text=None)
    service = ClassificationService(
        PlaceholderDocumentClassifier(), low_confidence_threshold=0.6
    )

    result = service.classify_document(document, db_session)

    assert result.classified_type is None
    assert result.classification_confidence is None

    events = db_session.query(AuditEvent).filter_by(entity_id=result.id).all()
    assert len(events) == 1
    assert events[0].event_type == "document_classification_skipped"


def test_skips_classification_when_extracted_text_is_blank(db_session: Session) -> None:
    document = _make_document(db_session, extracted_text="   ")
    service = ClassificationService(
        PlaceholderDocumentClassifier(), low_confidence_threshold=0.6
    )

    result = service.classify_document(document, db_session)

    assert result.classified_type is None


def test_low_confidence_is_recorded_and_flagged_in_audit(db_session: Session) -> None:
    """Der Platzhalter liefert immer niedrige Konfidenz - der Audit-Eintrag
    muss dokumentieren, dass manuelle Pruefung noetig ist."""
    document = _make_document(db_session, extracted_text="Ein neutraler Testtext.")
    service = ClassificationService(
        PlaceholderDocumentClassifier(), low_confidence_threshold=0.6
    )

    result = service.classify_document(document, db_session)

    assert result.classification_confidence is not None
    assert result.classification_confidence < 0.6

    events = db_session.query(AuditEvent).filter_by(entity_id=result.id).all()
    assert len(events) == 1
    assert events[0].event_type == "document_classified"
    assert "manuelle Prüfung erforderlich: True" in events[0].details
