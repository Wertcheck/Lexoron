"""Regressionsschutz: die Hintergrund-Endpunkte, die JEDE angemeldete
Seite per HTMX/fetch nachlädt (budget-badge, update-badge, lock-config -
siehe app/web/templates/base.html), müssen auch erreichbar bleiben, wenn
für den Nutzer eine Passwortänderung erzwungen ist
(`must_change_password=True`).

Gefunden bei einem echten Browser-Test dieses Schritts: ohne die Ausnahme
in `_PASSWORD_CHANGE_EXEMPT_PATHS` (app/auth/permissions.py) folgen
`fetch()`/HTMX dem 303-Redirect auf /dashboard/change-password und
erhalten die komplette HTML-Seite statt JSON/eines leeren Partials - bei
HTMX würde das die volle Seite in ein winziges <span> einschleusen."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models import User
from app.models.base import Base
from tests.auth_test_utils import login, seed_roles


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
def user_forced_to_change_password(db_session: Session) -> None:
    roles = seed_roles(db_session)
    user = User(
        email="muss-passwort-aendern@kanzlei.test",
        role_id=roles["mitarbeiter"].id,
        is_active=True,
        password_hash=hash_password("TestPasswort123"),
        must_change_password=True,
    )
    db_session.add(user)
    db_session.commit()


@pytest.mark.parametrize(
    "path",
    [
        "/dashboard/monitoring/budget-badge",
        "/dashboard/monitoring/update-badge",
        "/dashboard/lock-config",
    ],
)
def test_background_badge_endpoint_reachable_during_forced_password_change(
    client: TestClient, db_session: Session, user_forced_to_change_password, path: str
) -> None:
    login(client, "muss-passwort-aendern@kanzlei.test")

    response = client.get(path, follow_redirects=False)

    assert response.status_code == 200
    assert "Passwort ändern" not in response.text


def test_change_password_page_itself_still_forced(
    client: TestClient, db_session: Session, user_forced_to_change_password
) -> None:
    """Gegenprobe: die Ausnahme betrifft NUR die drei Hintergrund-
    Endpunkte - jede normale Dashboard-Seite bleibt weiterhin gesperrt,
    bis das Passwort geändert wurde."""
    login(client, "muss-passwort-aendern@kanzlei.test")

    response = client.get("/dashboard/inbox", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard/change-password"
