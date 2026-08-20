"""Tests für die PIN-Sperre über das Dashboard (Schritt 3, Teil 2):
Einrichtung, Sperren, Entsperren, Durchsetzung über require_login/
require_role."""

from __future__ import annotations

import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import User
from app.models.base import Base
from tests.auth_test_utils import create_test_user, login, seed_roles


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


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def roles(db_session: Session):
    return seed_roles(db_session)


def _csrf_from(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def test_set_pin_then_lock_then_dashboard_redirects_to_unlock(
    client: TestClient, db_session: Session, roles
) -> None:
    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")

    page = client.get("/dashboard/account/me")
    csrf = _csrf_from(page.text)

    set_pin_response = client.post(
        "/dashboard/account/me/set-pin",
        data={"csrf_token": csrf, "new_pin": "1234", "new_pin_confirm": "1234"},
        follow_redirects=False,
    )
    assert set_pin_response.status_code == 303

    lock_response = client.post(
        "/dashboard/lock-now", data={"csrf_token": csrf}, follow_redirects=False
    )
    assert lock_response.status_code == 303
    assert lock_response.headers["location"] == "/dashboard/unlock"

    inbox_response = client.get("/dashboard/inbox", follow_redirects=False)
    assert inbox_response.status_code == 303
    assert inbox_response.headers["location"] == "/dashboard/unlock"


def test_lock_now_without_pin_configured_is_a_harmless_noop(
    client: TestClient, db_session: Session, roles
) -> None:
    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")
    page = client.get("/dashboard/account/me")
    csrf = _csrf_from(page.text)

    response = client.post(
        "/dashboard/lock-now", data={"csrf_token": csrf}, follow_redirects=False
    )
    assert response.status_code == 303

    user = db_session.query(User).filter_by(email="mitarbeiter@kanzlei.test").first()
    assert user.is_locked is False


def test_unlock_with_correct_pin_restores_access(
    client: TestClient, db_session: Session, roles
) -> None:
    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")
    page = client.get("/dashboard/account/me")
    csrf = _csrf_from(page.text)
    client.post(
        "/dashboard/account/me/set-pin",
        data={"csrf_token": csrf, "new_pin": "1234", "new_pin_confirm": "1234"},
    )
    client.post("/dashboard/lock-now", data={"csrf_token": csrf})

    unlock_page = client.get("/dashboard/unlock")
    unlock_csrf = _csrf_from(unlock_page.text)
    unlock_response = client.post(
        "/dashboard/unlock",
        data={"csrf_token": unlock_csrf, "pin": "1234"},
        follow_redirects=False,
    )

    assert unlock_response.status_code == 303
    assert unlock_response.headers["location"] == "/dashboard/inbox"

    inbox_response = client.get("/dashboard/inbox")
    assert inbox_response.status_code == 200


def test_unlock_with_wrong_pin_stays_locked(
    client: TestClient, db_session: Session, roles
) -> None:
    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")
    page = client.get("/dashboard/account/me")
    csrf = _csrf_from(page.text)
    client.post(
        "/dashboard/account/me/set-pin",
        data={"csrf_token": csrf, "new_pin": "1234", "new_pin_confirm": "1234"},
    )
    client.post("/dashboard/lock-now", data={"csrf_token": csrf})

    unlock_page = client.get("/dashboard/unlock")
    unlock_csrf = _csrf_from(unlock_page.text)
    unlock_response = client.post(
        "/dashboard/unlock", data={"csrf_token": unlock_csrf, "pin": "0000"}
    )

    assert "Falsche PIN" in unlock_response.text or unlock_response.status_code == 303
    inbox_response = client.get("/dashboard/inbox", follow_redirects=False)
    assert inbox_response.status_code == 303
    assert inbox_response.headers["location"] == "/dashboard/unlock"


def test_mismatched_pin_confirmation_is_rejected(
    client: TestClient, db_session: Session, roles
) -> None:
    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")
    page = client.get("/dashboard/account/me")
    csrf = _csrf_from(page.text)

    client.post(
        "/dashboard/account/me/set-pin",
        data={"csrf_token": csrf, "new_pin": "1234", "new_pin_confirm": "5678"},
    )

    user = db_session.query(User).filter_by(email="mitarbeiter@kanzlei.test").first()
    assert user.pin_hash is None


def test_lock_config_reports_pin_status(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["anwalt"], "anwalt@kanzlei.test")
    login(client, "anwalt@kanzlei.test")

    response = client.get("/dashboard/lock-config")
    assert response.status_code == 200
    assert response.json()["pin_configured"] is False

    page = client.get("/dashboard/account/me")
    csrf = _csrf_from(page.text)
    client.post(
        "/dashboard/account/me/set-pin",
        data={"csrf_token": csrf, "new_pin": "1234", "new_pin_confirm": "1234"},
    )

    response = client.get("/dashboard/lock-config")
    assert response.json()["pin_configured"] is True


def test_clear_pin_removes_configuration(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["anwalt"], "anwalt@kanzlei.test")
    login(client, "anwalt@kanzlei.test")
    page = client.get("/dashboard/account/me")
    csrf = _csrf_from(page.text)
    client.post(
        "/dashboard/account/me/set-pin",
        data={"csrf_token": csrf, "new_pin": "1234", "new_pin_confirm": "1234"},
    )

    client.post("/dashboard/account/me/clear-pin", data={"csrf_token": csrf})

    user = db_session.query(User).filter_by(email="anwalt@kanzlei.test").first()
    assert user.pin_hash is None


def test_unauthenticated_unlock_page_redirects_to_login(client: TestClient) -> None:
    response = client.get("/dashboard/unlock", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard/login"
