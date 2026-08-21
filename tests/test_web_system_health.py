"""Tests für die neuen Selbstdiagnose-/Log-Endpunkte unter
/dashboard/monitoring (Schritt 3, Teil 2).

`get_settings` (app/config/settings.py) ist ein `@lru_cache`-Singleton fuer
den GESAMTEN Testprozess - jede echte HTTP-Anfrage in DIESER oder einer
ANDEREN Testdatei, die `APP_ENV=production` (o. Ae.) per `monkeypatch.setenv`
setzt UND dabei `get_settings()` (nicht nur `Settings()` direkt) ausloest,
haenterlaesst ohne eigenes `cache_clear()` einen fuer den Rest der Suite
"vergifteten" Cache (production-Settings ohne SESSION_SECRET_KEY -> harter
RuntimeError bei jedem folgenden Login/Auth-Check, siehe
Settings.resolved_session_secret_key). Bewusst defensiv: Cache vor UND nach
JEDEM Test in dieser Datei geleert, unabhaengig davon, welche andere
Testdatei zuvor lief oder folgt (derselbe Schutz wie in
tests/test_web_settings.py)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.base import Base
from tests.auth_test_utils import create_test_user, login, seed_roles


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
    assert "Claude-API-Schlüssel hinterlegt" in response.text
    assert "Claude-API-Erreichbarkeit" in response.text


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
    client: TestClient, db_session: Session, roles, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bewusst `get_settings` explizit auf 'kein Key' gepatcht statt auf die
    Umgebung zu vertrauen - eine lokale `.env` mit echtem
    ANTHROPIC_API_KEY (z. B. auf einem Entwicklungsrechner) würde diesen
    Test sonst nicht deterministisch machen (der Reachability-Check würde
    dann tatsächlich gegen die echte Anthropic-API laufen)."""
    import app.web.monitoring_router as monitoring_module
    from app.config import Settings

    monkeypatch.setattr(monitoring_module, "get_settings", lambda: Settings(anthropic_api_key=None))

    _login_admin(client, db_session, roles)
    page = client.get("/dashboard/monitoring")
    import re

    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)

    response = client.post("/dashboard/monitoring/check-api", data={"csrf_token": csrf})
    assert response.status_code == 200
    assert "nicht geprüft" in response.text


