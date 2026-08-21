"""Tests für app/document_generator/template_service.py (Block 3, 20.08.)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.document_generator.schema import DocumentTemplateInput
from app.document_generator.service import generate_from_template
from app.document_generator.template_service import (
    DocumentTemplateHasGeneratedDocumentsError,
    DocumentTemplateService,
)
from app.models import AuditEvent, Client, DocumentTemplate, Matter
from app.models.base import Base


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_create_template_persists_and_writes_audit_event(db_session: Session) -> None:
    service = DocumentTemplateService()
    data = DocumentTemplateInput(name="Mahnung", category="Mahnung", content="Sehr geehrte/r [Mandantenname]")
    template = service.create_template(db_session, data, actor="anwalt@kanzlei.test")

    assert template.version == 1
    assert db_session.query(DocumentTemplate).count() == 1
    events = db_session.query(AuditEvent).filter_by(entity_id=template.id).all()
    assert any(e.event_type == "document_template_created" for e in events)


def test_update_template_increments_version(db_session: Session) -> None:
    service = DocumentTemplateService()
    template = service.create_template(
        db_session,
        DocumentTemplateInput(name="Mahnung", content="Alt"),
        actor="anwalt@kanzlei.test",
    )
    updated = service.update_template(
        db_session,
        template,
        DocumentTemplateInput(name="Mahnung v2", content="Neu"),
        actor="anwalt@kanzlei.test",
    )
    assert updated.version == 2
    assert updated.content == "Neu"


def test_list_templates_orders_by_name(db_session: Session) -> None:
    service = DocumentTemplateService()
    service.create_template(db_session, DocumentTemplateInput(name="Zweite", content="x"), actor="a")
    service.create_template(db_session, DocumentTemplateInput(name="Erste", content="x"), actor="a")
    names = [t.name for t in service.list_templates(db_session)]
    assert names == ["Erste", "Zweite"]


def test_delete_template_without_generated_documents_succeeds(db_session: Session) -> None:
    service = DocumentTemplateService()
    template = service.create_template(
        db_session, DocumentTemplateInput(name="Loeschbar", content="x"), actor="a"
    )
    template_id = template.id
    service.delete_template(db_session, template, actor="a")
    assert db_session.get(DocumentTemplate, template_id) is None


def test_delete_template_used_for_generation_is_blocked(db_session: Session) -> None:
    """Kernanforderung: eine bereits verwendete Vorlage darf nicht
    geloescht werden - generierte Dokumente wuerden sonst ihre Herkunft
    verlieren."""
    service = DocumentTemplateService()
    template = service.create_template(
        db_session,
        DocumentTemplateInput(name="Verwendet", content="[Mandantenname]"),
        actor="a",
    )
    client = Client(name="Muster GmbH", client_number="M-1")
    db_session.add(client)
    db_session.flush()
    matter = Matter(client_id=client.id, title="Akte", status="open")
    db_session.add(matter)
    db_session.commit()

    generate_from_template(db_session, template, matter, actor="a")

    with pytest.raises(DocumentTemplateHasGeneratedDocumentsError):
        service.delete_template(db_session, template, actor="a")
    assert db_session.get(DocumentTemplate, template.id) is not None


def test_create_template_rejects_blank_name(db_session: Session) -> None:
    with pytest.raises(ValueError):
        DocumentTemplateInput(name="   ", content="x")


def test_create_template_rejects_blank_content(db_session: Session) -> None:
    with pytest.raises(ValueError):
        DocumentTemplateInput(name="Name", content="   ")
