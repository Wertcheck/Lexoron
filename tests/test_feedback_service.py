"""Tests fuer app/feedback/service.py (Prompt 13)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.feedback.schema import DraftFeedbackInput
from app.feedback.service import DraftFeedbackService
from app.knowledge.service import KnowledgeItemService
from app.models import AuditEvent, Client, Draft, DraftFeedback, KnowledgeItem, Matter
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


def _draft(db: Session, content: str = "Ursprünglicher KI-Entwurf") -> Draft:
    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte")
    draft = Draft(matter=matter, content=content)
    db.add_all([client, matter, draft])
    db.commit()
    return draft


def test_simple_approval_keeps_content_unchanged(db_session: Session) -> None:
    draft = _draft(db_session)
    service = DraftFeedbackService()

    feedback = service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="approved"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    assert feedback.original_content == "Ursprünglicher KI-Entwurf"
    assert feedback.edited_content is None
    assert draft.content == "Ursprünglicher KI-Entwurf"
    assert draft.status == "approved"
    assert draft.version == 1  # keine Aenderung -> keine neue Version


def test_approved_with_edits_updates_draft_and_increments_version(
    db_session: Session,
) -> None:
    draft = _draft(db_session)
    service = DraftFeedbackService()

    feedback = service.record_feedback(
        draft,
        DraftFeedbackInput(
            approval_status="approved_with_edits", edited_content="Korrigierter Entwurf"
        ),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    assert feedback.original_content == "Ursprünglicher KI-Entwurf"
    assert feedback.edited_content == "Korrigierter Entwurf"
    assert draft.content == "Korrigierter Entwurf"
    assert draft.version == 2
    assert draft.status == "approved"


def test_rejected_updates_draft_status_without_content_change(
    db_session: Session,
) -> None:
    draft = _draft(db_session)
    service = DraftFeedbackService()

    service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="rejected", comment="Falsche Rechtsgrundlage"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    assert draft.status == "rejected"
    assert draft.content == "Ursprünglicher KI-Entwurf"
    assert draft.version == 1


def test_record_feedback_creates_audit_event(db_session: Session) -> None:
    draft = _draft(db_session)
    service = DraftFeedbackService()

    service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="approved"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    events = db_session.query(AuditEvent).filter_by(entity_id=draft.id).all()
    assert len(events) == 1
    assert events[0].event_type == "draft_feedback_recorded"


def test_feedback_alone_never_creates_knowledge_item(db_session: Session) -> None:
    """Kernanforderung: Feedback speichern allein darf NIE Kanzleiwissen
    erzeugen - das erfordert den separaten promote_to_knowledge-Aufruf."""
    draft = _draft(db_session)
    service = DraftFeedbackService()

    service.record_feedback(
        draft,
        DraftFeedbackInput(
            approval_status="approved_with_edits", edited_content="Korrigierter Entwurf"
        ),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    assert db_session.query(KnowledgeItem).count() == 0


def test_promote_to_knowledge_creates_pending_item(db_session: Session) -> None:
    draft = _draft(db_session)
    service = DraftFeedbackService()
    feedback = service.record_feedback(
        draft,
        DraftFeedbackInput(
            approval_status="approved_with_edits", edited_content="Korrigierter Textbaustein"
        ),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    knowledge_item = service.promote_to_knowledge(
        feedback,
        db_session,
        title="Neuer Textbaustein aus Entwurf",
        actor="anwalt@kanzlei.test",
        category="Steuerrecht",
    )

    assert knowledge_item.content == "Korrigierter Textbaustein"
    # Wichtigste Regel: auch die bewusste Uebernahme ist NICHT automatisch
    # freigegeben.
    assert knowledge_item.approval_status == "pending"
    assert "draft_feedback_id" in (knowledge_item.source or "")


def test_promote_to_knowledge_falls_back_to_original_when_no_edit(
    db_session: Session,
) -> None:
    draft = _draft(db_session, content="Unveränderter Entwurfstext")
    service = DraftFeedbackService()
    feedback = service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="approved"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    knowledge_item = service.promote_to_knowledge(
        feedback, db_session, title="Baustein ohne Änderung", actor="anwalt@kanzlei.test"
    )

    assert knowledge_item.content == "Unveränderter Entwurfstext"


def test_promote_to_knowledge_creates_audit_event(db_session: Session) -> None:
    draft = _draft(db_session)
    service = DraftFeedbackService()
    feedback = service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="approved"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    service.promote_to_knowledge(
        feedback, db_session, title="Baustein", actor="anwalt@kanzlei.test"
    )

    events = db_session.query(AuditEvent).filter_by(
        entity_id=feedback.id, event_type="draft_feedback_promoted_to_knowledge"
    ).all()
    assert len(events) == 1


def test_multiple_feedback_entries_preserve_history(db_session: Session) -> None:
    """Zwei aufeinanderfolgende Feedback-Runden erzeugen zwei getrennte
    DraftFeedback-Eintraege mit je eigenem Original-Schnappschuss."""
    draft = _draft(db_session, content="Version 1")
    service = DraftFeedbackService()

    first = service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="approved_with_edits", edited_content="Version 2"),
        db_session,
        actor="anwalt@kanzlei.test",
    )
    second = service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="approved_with_edits", edited_content="Version 3"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    assert first.original_content == "Version 1"
    assert second.original_content == "Version 2"
    assert draft.content == "Version 3"
    assert draft.version == 3
    assert db_session.query(DraftFeedback).count() == 2
