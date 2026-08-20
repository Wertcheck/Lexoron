"""Tests für die neuen Selbstdiagnose-/Log-Endpunkte unter
/dashboard/monitoring (Schritt 3, Teil 2)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
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


def _login_admin(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["admin"], "admin@kanzlei.test")
    login(client, "admin@kanzlei.test")


def test_monitoring_page_shows_selbstdiagnose_section(
    client: TestClient, db_session: Session, roles
) -> None:
    _login_admin(client, db_session, roles)
    response = client.get("/dashboard/monitoring")
    assert response.status_code == 200
    assert "Selbstdiagnose" in response.text
    assert "nicht Teil dieser Installation" in response.text  # Ollama-Hinweis


def test_logs_preview_requires_admin(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")
    response = client.get("/dashboard/monitoring/logs-preview")
    assert response.status_code == 403


def test_logs_preview_without_configured_log_file(
    client: TestClient, db_session: Session, roles
) -> None:
    _login_admin(client, db_session, roles)
    response = client.get("/dashboard/monitoring/logs-preview")
    assert response.status_code == 200
    assert "Keine Log-Datei konfiguriert" in response.text


def test_logs_download_requires_admin(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["anwalt"], "anwalt@kanzlei.test")
    login(client, "anwalt@kanzlei.test")
    response = client.get("/dashboard/monitoring/logs/download")
    assert response.status_code == 403


def test_logs_download_returns_attachment(client: TestClient, db_session: Session, roles) -> None:
    _login_admin(client, db_session, roles)
    response = client.get("/dashboard/monitoring/logs/download")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]


def test_check_api_endpoint_requires_admin_and_csrf(
    client: TestClient, db_session: Session, roles
) -> None:
    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")
    response = client.post("/dashboard/monitoring/check-api", data={"csrf_token": "invalid"})
    assert response.status_code == 403


def test_check_api_endpoint_reports_not_configured_without_key(
    client: TestClient, db_session: Session, roles
) -> None:
    _login_admin(client, db_session, roles)
    page = client.get("/dashboard/monitoring")
    import re

    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)

    response = client.post("/dashboard/monitoring/check-api", data={"csrf_token": csrf})
    assert response.status_code == 200
    assert "nicht geprüft" in response.text
