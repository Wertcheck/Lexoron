"""Tests für die unaufdringlichen EUR-Softlimit-/Update-Hinweise (Schritt 3,
app/web/monitoring_router.py: budget_badge/update_badge) - sichtbar für
ALLE angemeldeten Rollen, nicht nur Admin.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.session import get_db
from app.main import app
from app.models import ApiCallLog
from app.models.base import Base
from app.updater.checker import UpdateCheckResult
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


def _login_mitarbeiter(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")


def test_budget_badge_empty_when_limit_not_reached(
    client: TestClient, db_session: Session, roles
) -> None:
    _login_mitarbeiter(client, db_session, roles)
    response = client.get("/dashboard/monitoring/budget-badge")
    assert response.status_code == 200
    assert "erreicht" not in response.text


def test_budget_badge_visible_to_non_admin_when_limit_reached(
    client: TestClient, db_session: Session, roles, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der EUR-Softlimit-Hinweis ist bewusst NICHT admin-only, anders als
    die detaillierte Systemstatus-Seite - siehe Modul-Docstring."""
    import app.web.monitoring_router as monitoring_module

    db_session.add(
        ApiCallLog(
            model="claude-sonnet-5",
            purpose="formulate_draft",
            estimated_cost_usd=1000.0,
            result_status="success",
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        monitoring_module,
        "get_settings",
        lambda: Settings(monthly_soft_limit_eur=1.0, usd_to_eur_rate=0.9),
    )

    _login_mitarbeiter(client, db_session, roles)
    response = client.get("/dashboard/monitoring/budget-badge")

    assert "erreicht" in response.text
    # Kein absoluter Betrag fuer Nicht-Admins - nur der Prozentsatz.
    assert "1000" not in response.text


def test_budget_badge_requires_login(client: TestClient) -> None:
    response = client.get("/dashboard/monitoring/budget-badge", follow_redirects=False)
    assert response.status_code == 303


def test_update_badge_empty_when_no_update_available(
    client: TestClient, db_session: Session, roles
) -> None:
    _login_mitarbeiter(client, db_session, roles)
    app.state.update_check = UpdateCheckResult(checked=True, update_available=False)
    response = client.get("/dashboard/monitoring/update-badge")
    assert response.status_code == 200
    assert "Update verfügbar" not in response.text


def test_update_badge_shows_link_when_update_available(
    client: TestClient, db_session: Session, roles
) -> None:
    _login_mitarbeiter(client, db_session, roles)
    app.state.update_check = UpdateCheckResult(
        checked=True,
        update_available=True,
        latest_version="0.2.0",
        download_url="https://example.invalid/setup.exe",
    )
    response = client.get("/dashboard/monitoring/update-badge")
    assert "0.2.0" in response.text
    assert "https://example.invalid/setup.exe" in response.text
