"""Tests für app/outbox/service.py (Prompt 25).

Schwerpunkt: keine Versandfähigkeit (strukturell, nicht nur per Test
behauptet - siehe test_outbox_service_module_has_no_send_capability),
korrekte Warteschlangen-/Statuslogik, Audit-Trail.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import AuditEvent, Client, Draft, Matter, OutboxEntry
from app.models.base import Base
from app.outbox.service import OutboxEntryAlreadyExistsError, OutboxService


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


def _draft(db: Session, content: str = "Freigegebener Entwurf.") -> Draft:
    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte")
    draft = Draft(matter=matter, content=content, status="approved")
    db.add_all([client, matter, draft])
    db.commit()
    return draft


# --- Grundregel: keine Versandfähigkeit ---


def test_outbox_service_module_has_no_send_capability() -> None:
    """Strukturelle Prüfung (nicht nur Verhalten): das Modul darf keine
    Methode besitzen, die auf 'send' o. ä. hindeutet - dieselbe Prüfung
    wie implizit beim MailProvider-Protocol (app/mail/base.py)."""
    method_names = [name for name in dir(OutboxService) if not name.startswith("_")]
    assert method_names == ["add_to_outbox", "mark_as_sent"]
    for name in method_names:
        assert "send" not in name or name == "mark_as_sent"
    # mark_as_sent selbst darf laut Quellcode keine Netzwerk-/SMTP-
    # Bibliothek importieren - grobe, aber wirksame Absicherung.
    import inspect

    source = inspect.getsource(OutboxService)
    for forbidden in ("smtplib", "requests.", "httpx.", "boto3", "sendgrid"):
        assert forbidden not in source


# --- add_to_outbox ---


def test_add_to_outbox_creates_pending_entry(db_session: Session) -> None:
    draft = _draft(db_session)
    service = OutboxService()

    entry = service.add_to_outbox(draft, db_session, actor="anwalt@kanzlei.test")

    assert entry.status == "pending"
    assert entry.draft_id == draft.id
    assert entry.matter_id == draft.matter_id
    assert entry.sent_at is None
    assert entry.sent_by is None


def test_add_to_outbox_writes_audit_event(db_session: Session) -> None:
    draft = _draft(db_session)
    service = OutboxService()

    entry = service.add_to_outbox(draft, db_session, actor="anwalt@kanzlei.test")

    events = db_session.query(AuditEvent).filter_by(entity_id=entry.id).all()
    assert len(events) == 1
    assert events[0].event_type == "draft_added_to_outbox"


def test_add_to_outbox_twice_raises(db_session: Session) -> None:
    draft = _draft(db_session)
    service = OutboxService()
    service.add_to_outbox(draft, db_session, actor="anwalt@kanzlei.test")

    with pytest.raises(OutboxEntryAlreadyExistsError):
        service.add_to_outbox(draft, db_session, actor="anwalt@kanzlei.test")


def test_add_to_outbox_twice_does_not_create_second_row(db_session: Session) -> None:
    draft = _draft(db_session)
    service = OutboxService()
    service.add_to_outbox(draft, db_session, actor="anwalt@kanzlei.test")
    try:
        service.add_to_outbox(draft, db_session, actor="anwalt@kanzlei.test")
    except OutboxEntryAlreadyExistsError:
        pass

    assert db_session.query(OutboxEntry).filter_by(draft_id=draft.id).count() == 1


# --- mark_as_sent ---


def test_mark_as_sent_sets_status_and_metadata(db_session: Session) -> None:
    draft = _draft(db_session)
    service = OutboxService()
    entry = service.add_to_outbox(draft, db_session, actor="anwalt@kanzlei.test")

    updated = service.mark_as_sent(entry, db_session, actor="anwalt@kanzlei.test")

    assert updated.status == "sent"
    assert updated.sent_at is not None
    assert updated.sent_by == "anwalt@kanzlei.test"


def test_mark_as_sent_writes_audit_event(db_session: Session) -> None:
    draft = _draft(db_session)
    service = OutboxService()
    entry = service.add_to_outbox(draft, db_session, actor="anwalt@kanzlei.test")

    service.mark_as_sent(entry, db_session, actor="anwalt@kanzlei.test")

    events = db_session.query(AuditEvent).filter_by(
        entity_id=entry.id, event_type="draft_marked_sent"
    ).all()
    assert len(events) == 1


def test_mark_as_sent_twice_raises(db_session: Session) -> None:
    draft = _draft(db_session)
    service = OutboxService()
    entry = service.add_to_outbox(draft, db_session, actor="anwalt@kanzlei.test")
    service.mark_as_sent(entry, db_session, actor="anwalt@kanzlei.test")

    with pytest.raises(ValueError):
        service.mark_as_sent(entry, db_session, actor="anwalt@kanzlei.test")


def test_mark_as_sent_preserves_original_sent_at_on_error(db_session: Session) -> None:
    draft = _draft(db_session)
    service = OutboxService()
    entry = service.add_to_outbox(draft, db_session, actor="anwalt@kanzlei.test")
    first = service.mark_as_sent(entry, db_session, actor="anwalt@kanzlei.test")
    first_sent_at = first.sent_at

    with pytest.raises(ValueError):
        service.mark_as_sent(entry, db_session, actor="jemand-anderes@kanzlei.test")

    db_session.expire_all()
    reloaded = db_session.get(OutboxEntry, entry.id)
    assert reloaded.sent_at == first_sent_at
    assert reloaded.sent_by == "anwalt@kanzlei.test"
