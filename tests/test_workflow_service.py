"""Tests fuer app/workflow/service.py (Prompt 20)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import AuditEvent, Client, Matter, WorkflowRun
from app.models.base import Base
from app.workflow import InvalidTransitionError, WorkflowStateMachine


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


def _matter(db: Session) -> Matter:
    client = Client(name="Max Mustermann")
    matter = Matter(client=client, title="Testakte")
    db.add_all([client, matter])
    db.commit()
    return matter


def test_create_workflow_run_starts_at_received(db_session: Session) -> None:
    sm = WorkflowStateMachine()
    matter = _matter(db_session)

    run = sm.create_workflow_run(db_session, matter_id=matter.id)

    assert run.status == "RECEIVED"
    assert run.matter_id == matter.id


def test_create_workflow_run_logs_audit_event(db_session: Session) -> None:
    sm = WorkflowStateMachine()
    matter = _matter(db_session)

    run = sm.create_workflow_run(db_session, matter_id=matter.id)

    events = db_session.query(AuditEvent).filter_by(
        entity_id=run.id, event_type="workflow_run_created"
    ).all()
    assert len(events) == 1


def test_valid_transition_updates_status(db_session: Session) -> None:
    sm = WorkflowStateMachine()
    matter = _matter(db_session)
    run = sm.create_workflow_run(db_session, matter_id=matter.id)

    updated = sm.transition(run.id, "PROCESSING", db_session)

    assert updated.status == "PROCESSING"


def test_valid_transition_logs_audit_event_with_both_states(db_session: Session) -> None:
    sm = WorkflowStateMachine()
    matter = _matter(db_session)
    run = sm.create_workflow_run(db_session, matter_id=matter.id)

    sm.transition(run.id, "PROCESSING", db_session)

    events = db_session.query(AuditEvent).filter_by(
        entity_id=run.id, event_type="workflow_transition"
    ).all()
    assert len(events) == 1
    assert events[0].details == "RECEIVED -> PROCESSING"


def test_invalid_transition_is_rejected_and_leaves_status_unchanged(
    db_session: Session,
) -> None:
    sm = WorkflowStateMachine()
    matter = _matter(db_session)
    run = sm.create_workflow_run(db_session, matter_id=matter.id)

    with pytest.raises(InvalidTransitionError):
        sm.transition(run.id, "APPROVED", db_session)  # RECEIVED -> APPROVED nicht erlaubt

    persisted = db_session.query(WorkflowRun).filter_by(id=run.id).first()
    assert persisted.status == "RECEIVED"


def test_unknown_status_is_rejected(db_session: Session) -> None:
    sm = WorkflowStateMachine()
    matter = _matter(db_session)
    run = sm.create_workflow_run(db_session, matter_id=matter.id)

    with pytest.raises(ValueError):
        sm.transition(run.id, "UNBEKANNT", db_session)


def test_raises_for_unknown_workflow_run(db_session: Session) -> None:
    sm = WorkflowStateMachine()
    with pytest.raises(ValueError):
        sm.transition("nicht-vorhanden", "PROCESSING", db_session)


def test_full_happy_path_to_archived(db_session: Session) -> None:
    sm = WorkflowStateMachine()
    matter = _matter(db_session)
    run = sm.create_workflow_run(db_session, matter_id=matter.id)

    for target in [
        "PROCESSING", "READY_FOR_REVIEW", "DRAFTED", "LEGAL_REVIEW", "APPROVED", "ARCHIVED",
    ]:
        run = sm.transition(run.id, target, db_session)

    assert run.status == "ARCHIVED"


def test_archived_has_no_valid_outgoing_transition(db_session: Session) -> None:
    sm = WorkflowStateMachine()
    matter = _matter(db_session)
    run = sm.create_workflow_run(db_session, matter_id=matter.id)
    for target in [
        "PROCESSING", "READY_FOR_REVIEW", "DRAFTED", "LEGAL_REVIEW", "APPROVED", "ARCHIVED",
    ]:
        run = sm.transition(run.id, target, db_session)

    with pytest.raises(InvalidTransitionError):
        sm.transition(run.id, "PROCESSING", db_session)


def test_error_reachable_from_processing_and_recoverable(db_session: Session) -> None:
    sm = WorkflowStateMachine()
    matter = _matter(db_session)
    run = sm.create_workflow_run(db_session, matter_id=matter.id)
    run = sm.transition(run.id, "PROCESSING", db_session)

    run = sm.transition(run.id, "ERROR", db_session, error_message="Testfehler")
    assert run.status == "ERROR"
    assert run.error_message == "Testfehler"

    run = sm.transition(run.id, "PROCESSING", db_session)
    assert run.status == "PROCESSING"


def test_legal_review_can_go_back_to_drafted_on_rejection(db_session: Session) -> None:
    """Konzept: 'Zurückweisen / Neu analysieren' in der Entwurfsansicht
    (Prompt 24) - eine Ablehnung fuehrt zurueck zum Entwurfsstadium."""
    sm = WorkflowStateMachine()
    matter = _matter(db_session)
    run = sm.create_workflow_run(db_session, matter_id=matter.id)
    for target in ["PROCESSING", "READY_FOR_REVIEW", "DRAFTED", "LEGAL_REVIEW"]:
        run = sm.transition(run.id, target, db_session)

    run = sm.transition(run.id, "DRAFTED", db_session)

    assert run.status == "DRAFTED"
