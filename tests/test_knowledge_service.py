"""Tests fuer app/knowledge/service.py (Prompt 12)."""

from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.knowledge.schema import KnowledgeItemImport
from app.knowledge.service import KnowledgeItemService
from app.models import AuditEvent, KnowledgeItem
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


def test_import_creates_pending_item_with_version_1(db_session: Session) -> None:
    service = KnowledgeItemService()
    data = KnowledgeItemImport(title="Kündigungsbaustein", content="Textinhalt")

    item = service.import_item(data, db_session)

    assert item.approval_status == "pending"
    assert item.version == 1
    assert item.id is not None


def test_import_creates_audit_event(db_session: Session) -> None:
    service = KnowledgeItemService()
    data = KnowledgeItemImport(title="Baustein", content="Inhalt")

    item = service.import_item(data, db_session, actor="anwalt@kanzlei.test")

    events = db_session.query(AuditEvent).filter_by(entity_id=item.id).all()
    assert len(events) == 1
    assert events[0].event_type == "knowledge_item_imported"
    assert events[0].actor == "anwalt@kanzlei.test"


def test_update_content_increments_version_and_resets_to_pending(
    db_session: Session,
) -> None:
    service = KnowledgeItemService()
    item = service.import_item(
        KnowledgeItemImport(title="Baustein", content="Alter Inhalt"), db_session
    )
    service.approve(item, db_session, actor="anwalt@kanzlei.test")
    assert item.approval_status == "approved"

    updated = service.update_content(
        item, "Neuer Inhalt", db_session, actor="anwalt@kanzlei.test"
    )

    assert updated.version == 2
    assert updated.content == "Neuer Inhalt"
    # Wichtigste Regel: Aenderung erfordert erneute Freigabe.
    assert updated.approval_status == "pending"


def test_update_content_rejects_blank_content(db_session: Session) -> None:
    service = KnowledgeItemService()
    item = service.import_item(
        KnowledgeItemImport(title="Baustein", content="Inhalt"), db_session
    )

    with pytest.raises(ValueError):
        service.update_content(item, "   ", db_session, actor="system")


def test_approve_sets_status_and_creates_audit_event(db_session: Session) -> None:
    service = KnowledgeItemService()
    item = service.import_item(
        KnowledgeItemImport(title="Baustein", content="Inhalt"), db_session
    )

    approved = service.approve(item, db_session, actor="anwalt@kanzlei.test")

    assert approved.approval_status == "approved"
    events = db_session.query(AuditEvent).filter_by(
        entity_id=item.id, event_type="knowledge_item_approved"
    ).all()
    assert len(events) == 1


def test_approve_triggers_indexing_when_search_service_provided(
    db_session: Session,
) -> None:
    class RecordingSearchService:
        def __init__(self) -> None:
            self.indexed_items: list[KnowledgeItem] = []

        def index_knowledge_item(self, item: KnowledgeItem, db: Session) -> None:
            self.indexed_items.append(item)

    search_service = RecordingSearchService()
    service = KnowledgeItemService(search_service=search_service)
    item = service.import_item(
        KnowledgeItemImport(title="Baustein", content="Inhalt"), db_session
    )

    service.approve(item, db_session, actor="system")

    assert len(search_service.indexed_items) == 1
    assert search_service.indexed_items[0].id == item.id


def test_deactivate_requires_reason(db_session: Session) -> None:
    service = KnowledgeItemService()
    item = service.import_item(
        KnowledgeItemImport(title="Baustein", content="Inhalt"), db_session
    )
    service.approve(item, db_session, actor="system")

    with pytest.raises(ValueError):
        service.deactivate(item, db_session, actor="system", reason="  ")


def test_deactivate_sets_status_and_logs_reason(db_session: Session) -> None:
    service = KnowledgeItemService()
    item = service.import_item(
        KnowledgeItemImport(title="Baustein", content="Inhalt"), db_session
    )
    service.approve(item, db_session, actor="system")

    deactivated = service.deactivate(
        item, db_session, actor="anwalt@kanzlei.test", reason="Nicht mehr aktuell"
    )

    assert deactivated.approval_status == "deactivated"
    events = db_session.query(AuditEvent).filter_by(
        entity_id=item.id, event_type="knowledge_item_deactivated"
    ).all()
    assert events[0].details == "Nicht mehr aktuell"


def test_list_items_filters_by_category_and_status(db_session: Session) -> None:
    service = KnowledgeItemService()
    item_a = service.import_item(
        KnowledgeItemImport(title="A", content="Inhalt A", category="Mietrecht"),
        db_session,
    )
    service.import_item(
        KnowledgeItemImport(title="B", content="Inhalt B", category="Arbeitsrecht"),
        db_session,
    )
    service.approve(item_a, db_session, actor="system")

    results = service.list_items(
        db_session, category="Mietrecht", approval_status="approved"
    )

    assert len(results) == 1
    assert results[0].id == item_a.id


def test_list_items_only_currently_valid_excludes_expired(
    db_session: Session,
) -> None:
    service = KnowledgeItemService()
    expired = service.import_item(
        KnowledgeItemImport(
            title="Abgelaufen",
            content="Inhalt",
            valid_until=date.today() - timedelta(days=1),
        ),
        db_session,
    )
    current = service.import_item(
        KnowledgeItemImport(title="Aktuell", content="Inhalt"), db_session
    )

    results = service.list_items(db_session, only_currently_valid=True)
    result_ids = {r.id for r in results}

    assert current.id in result_ids
    assert expired.id not in result_ids


def test_list_items_excludes_not_yet_valid(db_session: Session) -> None:
    service = KnowledgeItemService()
    future = service.import_item(
        KnowledgeItemImport(
            title="Zukünftig",
            content="Inhalt",
            valid_from=date.today() + timedelta(days=30),
        ),
        db_session,
    )

    results = service.list_items(db_session, only_currently_valid=True)
    result_ids = {r.id for r in results}

    assert future.id not in result_ids
