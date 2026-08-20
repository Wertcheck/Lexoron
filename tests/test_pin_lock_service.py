"""Tests für app/auth/pin_lock.py (Schritt 3, Teil 2)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.pin_lock import MAX_PIN_LENGTH, MIN_PIN_LENGTH, PinLockService, PinValidationError
from app.models import User
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


@pytest.fixture()
def user(db_session: Session) -> User:
    u = User(email="mitarbeiter@kanzlei.test", is_active=True)
    db_session.add(u)
    db_session.commit()
    return u


def test_set_pin_stores_hash_not_plaintext(db_session: Session, user: User) -> None:
    PinLockService().set_pin(db_session, user, "1234")
    assert user.pin_hash is not None
    assert "1234" not in user.pin_hash


def test_set_pin_rejects_non_digits(db_session: Session, user: User) -> None:
    with pytest.raises(PinValidationError):
        PinLockService().set_pin(db_session, user, "abcd")


@pytest.mark.parametrize("pin", ["1", "12", "123", "123456789"])
def test_set_pin_rejects_wrong_length(db_session: Session, user: User, pin: str) -> None:
    with pytest.raises(PinValidationError):
        PinLockService().set_pin(db_session, user, pin)


def test_set_pin_accepts_boundary_lengths(db_session: Session, user: User) -> None:
    PinLockService().set_pin(db_session, user, "1" * MIN_PIN_LENGTH)
    PinLockService().set_pin(db_session, user, "1" * MAX_PIN_LENGTH)


def test_lock_without_pin_configured_raises(db_session: Session, user: User) -> None:
    with pytest.raises(PinValidationError):
        PinLockService().lock(db_session, user)
    assert user.is_locked is False


def test_lock_and_unlock_roundtrip(db_session: Session, user: User) -> None:
    service = PinLockService()
    service.set_pin(db_session, user, "4321")
    service.lock(db_session, user)
    assert user.is_locked is True

    unlocked = service.unlock(db_session, user, "4321")

    assert unlocked is True
    assert user.is_locked is False


def test_unlock_with_wrong_pin_stays_locked(db_session: Session, user: User) -> None:
    service = PinLockService()
    service.set_pin(db_session, user, "4321")
    service.lock(db_session, user)

    unlocked = service.unlock(db_session, user, "0000")

    assert unlocked is False
    assert user.is_locked is True


def test_clear_pin_also_unlocks(db_session: Session, user: User) -> None:
    service = PinLockService()
    service.set_pin(db_session, user, "4321")
    service.lock(db_session, user)

    service.clear_pin(db_session, user)

    assert user.pin_hash is None
    assert user.is_locked is False
