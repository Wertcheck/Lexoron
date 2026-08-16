"""Tests für /dashboard/monitoring (Prompt 32) - NUR Admin, keine Secrets
in der Ausgabe.
"""

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


def test_admin_can_view_monitoring_page(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["admin"], "admin@kanzlei.test")
    login(client, "admin@kanzlei.test")
    response = client.get("/dashboard/monitoring")
    assert response.status_code == 200
    assert "Systemstatus" in response.text


@pytest.mark.parametrize("role_name", ["anwalt", "mitarbeiter"])
def test_non_admin_roles_are_denied(
    client: TestClient, db_session: Session, roles, role_name: str
) -> None:
    create_test_user(db_session, roles[role_name], f"{role_name}@kanzlei.test")
    login(client, f"{role_name}@kanzlei.test")
    response = client.get("/dashboard/monitoring")
    assert response.status_code == 403


def test_unauthenticated_access_is_denied(client: TestClient) -> None:
    response = client.get("/dashboard/monitoring", follow_redirects=False)
    assert response.status_code == 303
    assert "/dashboard/login" in response.headers["location"]


def test_monitoring_page_never_shows_actual_secret_values(
    client: TestClient, db_session: Session, roles, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Selbst wenn Secrets konfiguriert sind, dürfen NIEMALS ihre Werte
    erscheinen - nur Ja/Nein-Status."""
    import app.web.monitoring_router as monitoring_module
    from app.config import Settings

    fake_settings = Settings(
        anthropic_api_key="sk-ant-super-geheimer-test-schluessel-000000",
        mail_password="super-geheimes-mail-passwort",
    )
    monkeypatch.setattr(monitoring_module, "get_settings", lambda: fake_settings)

    create_test_user(db_session, roles["admin"], "admin@kanzlei.test")
    login(client, "admin@kanzlei.test")
    response = client.get("/dashboard/monitoring")

    assert "sk-ant-super-geheimer-test-schluessel" not in response.text
    assert "super-geheimes-mail-passwort" not in response.text
    assert "ja" in response.text.lower()  # Status wird trotzdem angezeigt


def test_monitoring_page_shows_pending_and_failed_error_counts(
    client: TestClient, db_session: Session, roles
) -> None:
    from app.errors import RetryService
    from app.models import Client, Document, Matter

    client_ = Client(name="Testmandant")
    matter = Matter(client=client_, title="Testakte")
    document = Document(
        matter=matter, original_filename="scan.pdf", file_path="/data/scan.pdf"
    )
    db_session.add_all([client_, matter, document])
    db_session.commit()

    retry_service = RetryService()
    retry_service.record_failure(
        db_session,
        entity_type="Document",
        entity_id=document.id,
        operation="ocr",
        error_category="transient",
        error_message="Testfehler",
    )

    create_test_user(db_session, roles["admin"], "admin@kanzlei.test")
    login(client, "admin@kanzlei.test")
    response = client.get("/dashboard/monitoring")

    assert "1</strong> wartend auf Wiederholung" in response.text
