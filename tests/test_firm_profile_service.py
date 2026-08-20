"""Tests für app/firm_profile/service.py (get_firm_profile)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.firm_profile import get_firm_profile
from app.models import FirmProfile
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


def test_creates_empty_profile_when_none_exists(db_session: Session) -> None:
    assert db_session.query(FirmProfile).count() == 0

    profile = get_firm_profile(db_session)

    assert profile.id is not None
    assert profile.firm_name == ""
    assert db_session.query(FirmProfile).count() == 1


def test_returns_existing_profile_without_creating_a_second(db_session: Session) -> None:
    existing = FirmProfile(firm_name="Bestehende Kanzlei")
    db_session.add(existing)
    db_session.commit()

    profile = get_firm_profile(db_session)

    assert profile.id == existing.id
    assert profile.firm_name == "Bestehende Kanzlei"
    assert db_session.query(FirmProfile).count() == 1
