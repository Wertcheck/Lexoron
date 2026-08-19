"""Web-Layer-Tests für die Platzhalterseiten (Prompt 48).

Deckt ab: alle vier Routen liefern 200 mit dem erwarteten Titel/Beschreibungs-
text (nicht als 404 oder stiller Redirect), erfordern eine Anmeldung wie
jede andere Dashboard-Seite, und bieten einen echten Rückweg zum Posteingang.
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
from tests.auth_test_utils import login_as_admin


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
        test_client = TestClient(app)
        login_as_admin(db_session, test_client)
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def anonymous_client(db_session: Session) -> Iterator[TestClient]:
    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("path", "expected_title"),
    [
        ("/dashboard/matters", "Akten"),
        ("/dashboard/sources", "Rechtsquellen"),
        ("/dashboard/knowledge", "Kanzlei-Wissen"),
        ("/dashboard/settings", "Einstellungen"),
    ],
)
def test_placeholder_page_returns_200_with_title(
    client: TestClient, path: str, expected_title: str
) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert expected_title in response.text
    assert "In Vorbereitung" in response.text


@pytest.mark.parametrize(
    "path",
    ["/dashboard/matters", "/dashboard/sources", "/dashboard/knowledge", "/dashboard/settings"],
)
def test_placeholder_page_links_back_to_inbox(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert 'href="/dashboard/inbox"' in response.text


@pytest.mark.parametrize(
    "path",
    ["/dashboard/matters", "/dashboard/sources", "/dashboard/knowledge", "/dashboard/settings"],
)
def test_unauthenticated_cannot_view_placeholder_page(
    anonymous_client: TestClient, path: str
) -> None:
    response = anonymous_client.get(path, follow_redirects=False)
    assert response.status_code == 303
    assert "/dashboard/login" in response.headers["location"]
