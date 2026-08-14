"""Tests fuer die Prompt-19-Erweiterungen an app/models/audit_event.py:
append-only-Erzwingung und Laengenbegrenzung."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import AuditEvent, AuditLogImmutableError
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


def test_updating_existing_event_is_blocked(db_session: Session) -> None:
    event = AuditEvent(
        entity_type="Test", entity_id="1", event_type="test", actor="system", details="Original"
    )
    db_session.add(event)
    db_session.commit()

    event.details = "Manipuliert"
    with pytest.raises(AuditLogImmutableError):
        db_session.commit()


def test_deleting_existing_event_is_blocked(db_session: Session) -> None:
    event = AuditEvent(entity_type="Test", entity_id="1", event_type="test", actor="system")
    db_session.add(event)
    db_session.commit()

    db_session.delete(event)
    with pytest.raises(AuditLogImmutableError):
        db_session.commit()


def test_details_within_limit_is_unchanged(db_session: Session) -> None:
    event = AuditEvent(
        entity_type="Test", entity_id="1", event_type="test", actor="system", details="Kurzer Text"
    )
    assert event.details == "Kurzer Text"


def test_details_exceeding_limit_is_truncated() -> None:
    long_text = "X" * 2000
    event = AuditEvent(entity_type="Test", entity_id="1", event_type="test", actor="system", details=long_text)

    assert len(event.details) == AuditEvent.MAX_DETAILS_LENGTH
    assert event.details.endswith("[…gekürzt]")


def test_details_none_stays_none() -> None:
    event = AuditEvent(entity_type="Test", entity_id="1", event_type="test", actor="system", details=None)
    assert event.details is None


def test_new_events_can_still_be_created_normally(db_session: Session) -> None:
    """Append-only bezieht sich auf AENDERUNGEN, nicht auf das normale
    Erzeugen neuer Ereignisse - das muss weiterhin problemlos funktionieren."""
    for i in range(3):
        db_session.add(
            AuditEvent(entity_type="Test", entity_id=str(i), event_type="test", actor="system")
        )
    db_session.commit()

    assert db_session.query(AuditEvent).count() == 3
