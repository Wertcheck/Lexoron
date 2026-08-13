"""Tests fuer app/matching/service.py (Prompt 09)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.matching.matcher import MatterMatchingService
from app.matching.service import MatterAssignmentService
from app.models import AuditEvent, Client, Document, Matter, Message
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


def _service(threshold: float = 0.6) -> MatterAssignmentService:
    matcher = MatterMatchingService(auto_assign_threshold=0.85, review_threshold=0.4)
    return MatterAssignmentService(
        matcher, classification_low_confidence_threshold=threshold
    )


def test_auto_assignment_sets_matter_id_and_cascades_to_documents(
    db_session: Session,
) -> None:
    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte", reference_number="A-3003")
    db_session.add_all([client, matter])
    db_session.commit()

    message = Message(direction="inbound", body_text="Az.: A-3003")
    document = Document(
        file_path="/tmp/anhang.pdf",
        classification_confidence=0.9,  # ausreichend sicher klassifiziert
    )
    message.documents.append(document)
    db_session.add(message)
    db_session.commit()

    result = _service().assign_matter(message, db_session)

    assert result.decision == "auto_assigned"
    assert message.matter_id == matter.id
    assert document.matter_id == matter.id


def test_needs_review_does_not_touch_matter_id(db_session: Session) -> None:
    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Unklare Akte ohne starke Signale")
    db_session.add_all([client, matter])
    db_session.commit()

    message = Message(direction="inbound", sender="unbekannt@example.test")
    db_session.add(message)
    db_session.commit()

    result = _service().assign_matter(message, db_session)

    assert result.decision in {"needs_review", "no_match"}
    assert message.matter_id is None


def test_missing_classification_blocks_auto_assignment(db_session: Session) -> None:
    """Dokument ganz ohne Klassifikation gilt als NICHT ausreichend sicher
    (sicherer Default) - selbst bei starkem Matching-Signal."""
    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte", reference_number="A-4004")
    db_session.add_all([client, matter])
    db_session.commit()

    message = Message(direction="inbound", body_text="Az.: A-4004")
    document = Document(file_path="/tmp/anhang.pdf")  # classification_confidence=None
    message.documents.append(document)
    db_session.add(message)
    db_session.commit()

    result = _service().assign_matter(message, db_session)

    assert result.decision == "needs_review"
    assert message.matter_id is None
    assert document.matter_id is None


def test_message_without_attachments_can_still_auto_assign(
    db_session: Session,
) -> None:
    """Keine Anhänge -> keine Klassifikation nötig -> classification_ok
    bleibt True."""
    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte", reference_number="A-5005")
    db_session.add_all([client, matter])
    db_session.commit()

    message = Message(direction="inbound", body_text="Az.: A-5005")
    db_session.add(message)
    db_session.commit()

    result = _service().assign_matter(message, db_session)

    assert result.decision == "auto_assigned"
    assert message.matter_id == matter.id


def test_assignment_creates_audit_event(db_session: Session) -> None:
    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte", reference_number="A-6006")
    db_session.add_all([client, matter])
    db_session.commit()

    message = Message(direction="inbound", body_text="Az.: A-6006")
    db_session.add(message)
    db_session.commit()

    _service().assign_matter(message, db_session)

    events = db_session.query(AuditEvent).filter_by(entity_id=message.id).all()
    assert len(events) == 1
    assert events[0].entity_type == "Message"
    assert events[0].event_type == "matter_match_auto_assigned"
