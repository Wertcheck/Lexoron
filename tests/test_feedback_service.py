"""Tests fuer app/feedback/service.py (Prompt 13, Versionierung ab Prompt 23).

Seit Prompt 23 erzeugt "approved_with_edits" eine NEUE `Draft`-Version
statt die bestehende Zeile zu ueberschreiben - siehe
app/drafting/versioning.py. Diese Tests pruefen entsprechend beide
Zeilen (Original UNVERAENDERT, neue Version korrekt verkettet).
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.feedback.schema import DraftFeedbackInput
from app.feedback.service import DraftFeedbackService
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

    result = service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="approved"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    assert result.feedback.original_content == "Ursprünglicher KI-Entwurf"
    assert result.feedback.edited_content is None
    assert result.draft.content == "Ursprünglicher KI-Entwurf"
    assert result.draft.status == "approved"
    assert result.draft.version == 1  # keine Aenderung -> keine neue Version
    assert result.new_draft is None  # keine Bearbeitung -> keine neue Zeile


def test_approved_with_edits_creates_new_version_without_mutating_original(
    db_session: Session,
) -> None:
    """Kernanforderung Prompt 23: die urspruengliche Draft-Zeile wird bei
    einer Bearbeitung NIE ueberschrieben - weder Inhalt noch Status."""
    draft = _draft(db_session)
    original_id = draft.id
    service = DraftFeedbackService()

    result = service.record_feedback(
        draft,
        DraftFeedbackInput(
            approval_status="approved_with_edits", edited_content="Korrigierter Entwurf"
        ),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    # Die URSPRUENGLICHE Zeile bleibt komplett unangetastet.
    assert result.draft.id == original_id
    assert result.draft.content == "Ursprünglicher KI-Entwurf"
    assert result.draft.version == 1
    assert result.draft.status == "draft"  # NICHT auf "approved" gesetzt

    # Die NEUE Version traegt die Aenderung.
    assert result.new_draft is not None
    assert result.new_draft.id != original_id
    assert result.new_draft.content == "Korrigierter Entwurf"
    assert result.new_draft.version == 2
    assert result.new_draft.status == "approved"
    assert result.new_draft.previous_version_id == original_id

    assert result.feedback.original_content == "Ursprünglicher KI-Entwurf"
    assert result.feedback.edited_content == "Korrigierter Entwurf"
    # Das Feedback bezieht sich weiterhin auf die bewertete (alte) Version.
    assert result.feedback.draft_id == original_id


def test_rejected_updates_draft_status_without_content_change(
    db_session: Session,
) -> None:
    draft = _draft(db_session)
    service = DraftFeedbackService()

    result = service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="rejected", comment="Falsche Rechtsgrundlage"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    assert result.draft.status == "rejected"
    assert result.draft.content == "Ursprünglicher KI-Entwurf"
    assert result.draft.version == 1
    assert result.new_draft is None


def test_record_feedback_creates_expected_audit_events(db_session: Session) -> None:
    draft = _draft(db_session)
    service = DraftFeedbackService()

    service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="approved"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    events = db_session.query(AuditEvent).filter_by(entity_id=draft.id).all()
    event_types = {e.event_type for e in events}
    assert "draft_feedback_recorded" in event_types
    assert "draft_approved" in event_types


def test_rejected_creates_draft_rejected_audit_event(db_session: Session) -> None:
    draft = _draft(db_session)
    service = DraftFeedbackService()

    service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="rejected", comment="Nicht ausreichend"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    events = db_session.query(AuditEvent).filter_by(entity_id=draft.id).all()
    event_types = {e.event_type for e in events}
    assert "draft_rejected" in event_types
    assert "draft_approved" not in event_types


def test_approved_with_edits_creates_manual_edit_and_version_created_events_on_new_draft(
    db_session: Session,
) -> None:
    draft = _draft(db_session)
    service = DraftFeedbackService()

    result = service.record_feedback(
        draft,
        DraftFeedbackInput(
            approval_status="approved_with_edits", edited_content="Korrigierter Entwurf"
        ),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    new_draft_events = (
        db_session.query(AuditEvent).filter_by(entity_id=result.new_draft.id).all()
    )
    event_types = {e.event_type for e in new_draft_events}
    assert "draft_version_created" in event_types
    assert "draft_manual_edit" in event_types
    assert "draft_approved" in event_types
    # Auf der ALTEN Zeile darf KEIN "draft_approved"/"draft_manual_edit"
    # auftauchen - der Ausgang gehoert zur neuen Version.
    old_draft_events = db_session.query(AuditEvent).filter_by(entity_id=draft.id).all()
    old_event_types = {e.event_type for e in old_draft_events}
    assert "draft_approved" not in old_event_types
    assert "draft_manual_edit" not in old_event_types


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
    result = service.record_feedback(
        draft,
        DraftFeedbackInput(
            approval_status="approved_with_edits", edited_content="Korrigierter Textbaustein"
        ),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    knowledge_item = service.promote_to_knowledge(
        result.feedback,
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
    result = service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="approved"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    knowledge_item = service.promote_to_knowledge(
        result.feedback, db_session, title="Baustein ohne Änderung", actor="anwalt@kanzlei.test"
    )

    assert knowledge_item.content == "Unveränderter Entwurfstext"


def test_promote_to_knowledge_creates_audit_event(db_session: Session) -> None:
    draft = _draft(db_session)
    service = DraftFeedbackService()
    result = service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="approved"),
        db_session,
        actor="anwalt@kanzlei.test",
    )

    service.promote_to_knowledge(
        result.feedback, db_session, title="Baustein", actor="anwalt@kanzlei.test"
    )

    events = db_session.query(AuditEvent).filter_by(
        entity_id=result.feedback.id, event_type="draft_feedback_promoted_to_knowledge"
    ).all()
    assert len(events) == 1


def test_multiple_feedback_rounds_build_a_version_chain(db_session: Session) -> None:
    """Zwei aufeinanderfolgende Bearbeitungsrunden erzeugen eine
    nachvollziehbare Versionskette v1 -> v2 -> v3, JEDE Zeile bleibt nach
    ihrer Entstehung unveraendert; zwei getrennte DraftFeedback-Eintraege
    mit je eigenem Original-Schnappschuss."""
    draft_v1 = _draft(db_session, content="Version 1")
    service = DraftFeedbackService()

    first = service.record_feedback(
        draft_v1,
        DraftFeedbackInput(approval_status="approved_with_edits", edited_content="Version 2"),
        db_session,
        actor="anwalt@kanzlei.test",
    )
    draft_v2 = first.new_draft
    assert draft_v2 is not None

    second = service.record_feedback(
        draft_v2,
        DraftFeedbackInput(approval_status="approved_with_edits", edited_content="Version 3"),
        db_session,
        actor="anwalt@kanzlei.test",
    )
    draft_v3 = second.new_draft
    assert draft_v3 is not None

    assert first.feedback.original_content == "Version 1"
    assert second.feedback.original_content == "Version 2"

    # v1 unveraendert.
    assert draft_v1.content == "Version 1"
    assert draft_v1.version == 1
    assert draft_v1.previous_version_id is None
    # v2 unveraendert (nachdem v3 aus ihr entstanden ist).
    assert draft_v2.content == "Version 2"
    assert draft_v2.version == 2
    assert draft_v2.previous_version_id == draft_v1.id
    # v3 aktuelle Version.
    assert draft_v3.content == "Version 3"
    assert draft_v3.version == 3
    assert draft_v3.previous_version_id == draft_v2.id

    assert db_session.query(Draft).count() == 3
    assert db_session.query(DraftFeedback).count() == 2
