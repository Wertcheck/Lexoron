"""Tests für app/prompt_library/service.py (Schritt 3, Teil 2)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import AuditEvent, PromptTemplate
from app.models.base import Base
from app.prompt_library.schema import PromptTemplateInput
from app.prompt_library.service import PromptTemplateService


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


def test_create_template_starts_at_version_one(db_session: Session) -> None:
    data = PromptTemplateInput(
        name="Fristverlängerung anfragen",
        content="Sehr geehrte/r {Mandant}, wir beantragen eine Fristverlängerung bis {Frist}.",
    )
    template = PromptTemplateService().create_template(db_session, data, actor="anwalt@kanzlei.test")

    assert template.version == 1
    assert template.created_by_actor == "anwalt@kanzlei.test"


def test_update_template_increments_version(db_session: Session) -> None:
    service = PromptTemplateService()
    template = service.create_template(
        db_session,
        PromptTemplateInput(name="Vorlage", content="Text mit {Mandant}"),
        actor="anwalt@kanzlei.test",
    )

    updated = service.update_template(
        db_session,
        template,
        PromptTemplateInput(name="Vorlage", content="Geänderter Text mit {Mandant}"),
        actor="admin@kanzlei.test",
    )

    assert updated.version == 2
    assert updated.updated_by_actor == "admin@kanzlei.test"
    assert updated.content == "Geänderter Text mit {Mandant}"


def test_delete_template_removes_row(db_session: Session) -> None:
    service = PromptTemplateService()
    template = service.create_template(
        db_session,
        PromptTemplateInput(name="Vorlage", content="Text"),
        actor="anwalt@kanzlei.test",
    )

    service.delete_template(db_session, template, actor="admin@kanzlei.test")

    assert db_session.query(PromptTemplate).count() == 0


def test_list_templates_sorted_by_name(db_session: Session) -> None:
    service = PromptTemplateService()
    service.create_template(
        db_session, PromptTemplateInput(name="Zeta", content="x"), actor="a@kanzlei.test"
    )
    service.create_template(
        db_session, PromptTemplateInput(name="Alpha", content="x"), actor="a@kanzlei.test"
    )

    names = [t.name for t in service.list_templates(db_session)]

    assert names == ["Alpha", "Zeta"]


def test_create_and_update_and_delete_create_audit_events(db_session: Session) -> None:
    service = PromptTemplateService()
    template = service.create_template(
        db_session, PromptTemplateInput(name="Vorlage", content="Text"), actor="a@kanzlei.test"
    )
    service.update_template(
        db_session,
        template,
        PromptTemplateInput(name="Vorlage", content="Neuer Text"),
        actor="a@kanzlei.test",
    )
    service.delete_template(db_session, template, actor="a@kanzlei.test")

    event_types = {
        event.event_type
        for event in db_session.query(AuditEvent).filter_by(entity_type="PromptTemplate").all()
    }
    assert event_types == {
        "prompt_template_created",
        "prompt_template_updated",
        "prompt_template_deleted",
    }
