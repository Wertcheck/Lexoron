"""Web-Layer-Tests für die Platzhalterseiten (Prompt 48, erweitert Prompt 49).

Deckt ab: alle Platzhalter-Routen liefern 200 mit dem erwarteten Titel/
Beschreibungstext (nicht als 404 oder stiller Redirect), erfordern eine
Anmeldung wie jede andere Dashboard-Seite, bieten einen echten Rückweg zum
Posteingang, und die alte generische "Einstellungen"-Route aus Prompt 48
leitet auf den neuen Profil-/Einstellungen-Bereich (Prompt 49) weiter statt
einen 404 zu liefern.
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


_PLACEHOLDER_CASES = [
    ("/dashboard/recent", "Letzte Akten"),
    ("/dashboard/matters", "Aktive Akten"),
    ("/dashboard/documents", "Dokumenten-Viewer"),
    ("/dashboard/archive", "Archiv"),
    ("/dashboard/tools/schriftsatz", "Schriftsatz-Generator"),
    ("/dashboard/tools/fristen", "Fristen-Check"),
    ("/dashboard/tools/zeitleiste", "Zeitleiste"),
    ("/dashboard/tools/beleg-extraktion", "Beleg-Extraktion"),
    ("/dashboard/sources", "Rechtsquellen"),
    ("/dashboard/library/mustertexte", "Kanzlei-Mustertexte"),
    ("/dashboard/library/prompts", "Standard-Prompts"),
    ("/dashboard/knowledge", "Kanzlei-Wissen"),
    ("/dashboard/history/analysen", "Gespeicherte Analysen"),
    ("/dashboard/account/profile", "Kanzlei-Profil & Briefkopf"),
    ("/dashboard/account/license", "System & Lizenz"),
]


@pytest.mark.parametrize(("path", "expected_title"), _PLACEHOLDER_CASES)
def test_placeholder_page_returns_200_with_title(
    client: TestClient, path: str, expected_title: str
) -> None:
    response = client.get(path)
    assert response.status_code == 200
    # placeholder.html rendert den Titel ueber {{ placeholder_title }} - Jinja
    # escaped "&" dabei automatisch zu "&amp;" (anders als die Sidebar-Labels
    # in base.html, die als literaler Template-Text nicht escaped werden).
    assert expected_title.replace("&", "&amp;") in response.text
    assert "In Vorbereitung" in response.text


@pytest.mark.parametrize(("path", "_expected_title"), _PLACEHOLDER_CASES)
def test_placeholder_page_links_back_to_inbox(
    client: TestClient, path: str, _expected_title: str
) -> None:
    response = client.get(path)
    assert 'href="/dashboard/inbox"' in response.text


@pytest.mark.parametrize(("path", "_expected_title"), _PLACEHOLDER_CASES)
def test_unauthenticated_cannot_view_placeholder_page(
    anonymous_client: TestClient, path: str, _expected_title: str
) -> None:
    response = anonymous_client.get(path, follow_redirects=False)
    assert response.status_code == 303
    assert "/dashboard/login" in response.headers["location"]


def test_old_settings_route_redirects_to_account_overview(client: TestClient) -> None:
    """Prompt 48s generische "Einstellungen"-Platzhalterseite wurde in
    Prompt 49 durch den strukturierten Profil-/Einstellungen-Bereich
    ersetzt - alte Links (z. B. Lesezeichen) sollen trotzdem funktionieren,
    kein 404."""
    response = client.get("/dashboard/settings", follow_redirects=False)
    assert response.status_code in (302, 303, 307, 308)
    assert response.headers["location"] == "/dashboard/account"
