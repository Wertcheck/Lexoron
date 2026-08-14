"""Tests fuer app/promptlayer/policy_service.py (Prompt 16)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import AuditEvent, Policy
from app.models.base import Base
from app.promptlayer.policy_service import PolicyService


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


def test_first_version_is_version_1(db_session: Session) -> None:
    service = PolicyService()

    policy = service.create_version(
        "default", "Schreibe formell.", db_session, actor="anwalt@kanzlei.test"
    )

    assert policy.version == 1
    assert policy.is_active is True


def test_second_version_increments_and_deactivates_first(db_session: Session) -> None:
    service = PolicyService()
    first = service.create_version(
        "default", "Version eins", db_session, actor="anwalt@kanzlei.test"
    )

    second = service.create_version(
        "default", "Version zwei", db_session, actor="anwalt@kanzlei.test"
    )

    assert second.version == 2
    assert second.is_active is True
    db_session.refresh(first)
    assert first.is_active is False


def test_get_active_policy_returns_latest(db_session: Session) -> None:
    service = PolicyService()
    service.create_version("default", "Alt", db_session, actor="system")
    service.create_version("default", "Neu", db_session, actor="system")

    active = service.get_active_policy("default", db_session)

    assert active is not None
    assert active.content == "Neu"


def test_get_active_policy_returns_none_when_unset(db_session: Session) -> None:
    service = PolicyService()

    assert service.get_active_policy("nicht-vorhanden", db_session) is None


def test_blank_content_is_rejected(db_session: Session) -> None:
    service = PolicyService()

    with pytest.raises(ValueError):
        service.create_version("default", "   ", db_session, actor="system")


def test_different_policy_names_are_independent(db_session: Session) -> None:
    service = PolicyService()
    service.create_version("default", "Standard-Regeln", db_session, actor="system")
    service.create_version("steuerrecht", "Steuerrecht-Regeln", db_session, actor="system")

    default_policy = service.get_active_policy("default", db_session)
    tax_policy = service.get_active_policy("steuerrecht", db_session)

    assert default_policy.version == 1
    assert tax_policy.version == 1
    assert default_policy.content != tax_policy.content


def test_create_version_creates_audit_event(db_session: Session) -> None:
    service = PolicyService()

    policy = service.create_version(
        "default", "Regeltext", db_session, actor="anwalt@kanzlei.test"
    )

    events = db_session.query(AuditEvent).filter_by(entity_id=policy.id).all()
    assert len(events) == 1
    assert events[0].event_type == "policy_version_created"


def test_old_versions_remain_in_database(db_session: Session) -> None:
    service = PolicyService()
    service.create_version("default", "Version eins", db_session, actor="system")
    service.create_version("default", "Version zwei", db_session, actor="system")

    all_versions = db_session.query(Policy).filter_by(name="default").all()

    assert len(all_versions) == 2
