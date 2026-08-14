"""Tests fuer app/audit/service.py (Prompt 19).

Schwerpunkt: Aktenisolation - Abfrage fuer Akte A darf niemals Ereignisse
aus Akte B enthalten."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.audit import AuditLogService
from app.models import AuditEvent, Client, Deadline, Document, Draft, Matter
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


def _matter(db: Session, title: str = "Testakte") -> Matter:
    client = Client(name=f"Mandant für {title}")
    matter = Matter(client=client, title=title)
    db.add_all([client, matter])
    db.commit()
    return matter


def test_list_events_for_entity_returns_matching_events(db_session: Session) -> None:
    service = AuditLogService()
    db_session.add(
        AuditEvent(entity_type="Document", entity_id="doc-1", event_type="x", actor="system")
    )
    db_session.add(
        AuditEvent(entity_type="Document", entity_id="doc-2", event_type="y", actor="system")
    )
    db_session.commit()

    events = service.list_events_for_entity("Document", "doc-1", db_session)

    assert len(events) == 1
    assert events[0].event_type == "x"


def test_list_events_for_matter_requires_matter_id() -> None:
    service = AuditLogService()
    with pytest.raises(ValueError):
        service.list_events_for_matter("", db=None)  # type: ignore[arg-type]


def test_list_events_for_matter_includes_matter_level_events(db_session: Session) -> None:
    matter = _matter(db_session)
    db_session.add(
        AuditEvent(
            entity_type="Matter", entity_id=matter.id, event_type="legal_research_performed", actor="system"
        )
    )
    db_session.commit()
    service = AuditLogService()

    events = service.list_events_for_matter(matter.id, db_session)

    assert len(events) == 1
    assert events[0].event_type == "legal_research_performed"


def test_list_events_for_matter_includes_document_events(db_session: Session) -> None:
    matter = _matter(db_session)
    document = Document(matter=matter, file_path="/tmp/x.pdf")
    db_session.add(document)
    db_session.commit()
    db_session.add(
        AuditEvent(
            entity_type="Document", entity_id=document.id, event_type="document_classified", actor="system"
        )
    )
    db_session.commit()
    service = AuditLogService()

    events = service.list_events_for_matter(matter.id, db_session)

    assert any(e.event_type == "document_classified" for e in events)


def test_list_events_for_matter_includes_deadline_and_draft_events(
    db_session: Session,
) -> None:
    matter = _matter(db_session)
    deadline = Deadline(matter=matter, source_text="Frist")
    draft = Draft(matter=matter, content="Text")
    db_session.add_all([deadline, draft])
    db_session.commit()
    db_session.add(
        AuditEvent(entity_type="Deadline", entity_id=deadline.id, event_type="deadline_created", actor="system")
    )
    db_session.add(
        AuditEvent(entity_type="Draft", entity_id=draft.id, event_type="draft_created", actor="system")
    )
    db_session.commit()
    service = AuditLogService()

    events = service.list_events_for_matter(matter.id, db_session)
    event_types = {e.event_type for e in events}

    assert "deadline_created" in event_types
    assert "draft_created" in event_types


def test_list_events_for_matter_never_includes_other_matter(db_session: Session) -> None:
    """Kernanforderung: strikte Aktenisolation."""
    matter_a = _matter(db_session, title="Akte A")
    matter_b = _matter(db_session, title="Akte B")
    document_a = Document(matter=matter_a, file_path="/tmp/a.pdf")
    document_b = Document(matter=matter_b, file_path="/tmp/b.pdf")
    db_session.add_all([document_a, document_b])
    db_session.commit()
    db_session.add(
        AuditEvent(entity_type="Document", entity_id=document_a.id, event_type="a_event", actor="system")
    )
    db_session.add(
        AuditEvent(entity_type="Document", entity_id=document_b.id, event_type="b_event", actor="system")
    )
    db_session.add(
        AuditEvent(entity_type="Matter", entity_id=matter_b.id, event_type="b_matter_event", actor="system")
    )
    db_session.commit()
    service = AuditLogService()

    events_a = service.list_events_for_matter(matter_a.id, db_session)
    event_types_a = {e.event_type for e in events_a}

    assert "a_event" in event_types_a
    assert "b_event" not in event_types_a
    assert "b_matter_event" not in event_types_a


def test_list_events_for_matter_with_no_events_returns_empty_list(
    db_session: Session,
) -> None:
    matter = _matter(db_session)
    service = AuditLogService()

    events = service.list_events_for_matter(matter.id, db_session)

    assert events == []


def test_list_events_for_matter_orders_chronologically(db_session: Session) -> None:
    matter = _matter(db_session)
    first = AuditEvent(entity_type="Matter", entity_id=matter.id, event_type="first", actor="system")
    db_session.add(first)
    db_session.commit()
    second = AuditEvent(entity_type="Matter", entity_id=matter.id, event_type="second", actor="system")
    db_session.add(second)
    db_session.commit()
    service = AuditLogService()

    events = service.list_events_for_matter(matter.id, db_session)

    assert [e.event_type for e in events] == ["first", "second"]


def test_excludes_firm_wide_knowledge_and_source_events(db_session: Session) -> None:
    """KnowledgeItem/Source/Policy sind kanzleiweit, nicht aktenbezogen -
    ihre Events duerfen NICHT in einer Akten-Abfrage auftauchen."""
    matter = _matter(db_session)
    db_session.add(
        AuditEvent(
            entity_type="KnowledgeItem", entity_id="ki-1", event_type="knowledge_item_approved", actor="system"
        )
    )
    db_session.commit()
    service = AuditLogService()

    events = service.list_events_for_matter(matter.id, db_session)

    assert not any(e.entity_type == "KnowledgeItem" for e in events)
