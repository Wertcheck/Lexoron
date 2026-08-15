"""Tests fuer das serverseitig gerenderte Dashboard (Prompt 22 - Inbox).

Gleiches Testmuster wie tests/test_api.py: geteilte In-Memory-SQLite-DB
ueber `app.dependency_overrides`, StaticPool wegen FastAPIs Thread-Pool
(siehe ausfuehrliche Begruendung dort).
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
from app.models import Client, Document, Matter, Message
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
def seeded(db_session: Session) -> dict[str, str]:
    """Ausschliesslich synthetische Testdaten (Grundregel) - ein Mandant,
    eine Akte, eine zugeordnete und eine nicht zugeordnete Nachricht, ein
    Dokument als Anhang der zugeordneten Nachricht."""
    mandant = Client(name="Synthetischer Testmandant GmbH")
    db_session.add(mandant)
    db_session.flush()

    matter = Matter(
        client_id=mandant.id,
        title="Einspruch Steuerbescheid 2025",
        reference_number="2025/0142-ESt",
    )
    db_session.add(matter)
    db_session.flush()

    matched = Message(
        matter_id=matter.id,
        direction="inbound",
        sender="j.mueller@steuerkanzlei-test.invalid",
        subject="Steuerbescheid 2025 - Einspruchsfrist beachten",
        body_text="Testinhalt, keine echten Mandantendaten.",
    )
    unmatched = Message(
        matter_id=None,
        direction="inbound",
        sender="neuermandant@example-testdomain.invalid",
        subject="Anfrage: Betriebspruefung angekuendigt",
        body_text="Testinhalt.",
    )
    outbound = Message(
        matter_id=matter.id,
        direction="outbound",
        sender="kanzlei@steuerkanzlei-test.invalid",
        subject="RE: Steuerbescheid 2025",
        body_text="Testinhalt.",
    )
    db_session.add_all([matched, unmatched, outbound])
    db_session.flush()

    document = Document(
        matter_id=matter.id,
        message_id=matched.id,
        original_filename="steuerbescheid_2025_test.pdf",
        file_path="/data/intake/test/steuerbescheid_2025_test.pdf",
        classified_type="steuerbescheid",
    )
    db_session.add(document)
    db_session.commit()

    return {
        "matter_id": matter.id,
        "matched_message_id": matched.id,
        "unmatched_message_id": unmatched.id,
        "outbound_message_id": outbound.id,
        "document_id": document.id,
    }


# --- Grundfunktionen ---


def test_dashboard_root_redirects_to_inbox(client: TestClient) -> None:
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard/inbox"


def test_inbox_page_returns_200(client: TestClient, seeded: dict) -> None:
    response = client.get("/dashboard/inbox")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_static_css_is_served(client: TestClient) -> None:
    response = client.get("/dashboard/static/css/app.css")
    assert response.status_code == 200


def test_static_htmx_is_served_locally(client: TestClient) -> None:
    """Grundregel Prompt 22: HTMX wird lokal ausgeliefert, nicht per CDN
    (Offline-first-Prinzip, siehe app/web/static/js/VENDORED.md)."""
    response = client.get("/dashboard/static/js/htmx.min.js")
    assert response.status_code == 200
    assert len(response.content) > 1000


# --- Inhalt / Aktenisolation-Badges ---


def test_inbox_shows_matched_message_with_reference_number(
    client: TestClient, seeded: dict
) -> None:
    response = client.get("/dashboard/inbox")
    assert "2025/0142-ESt" in response.text
    assert "Steuerbescheid 2025" in response.text


def test_inbox_shows_unmatched_badge_for_message_without_matter(
    client: TestClient, seeded: dict
) -> None:
    response = client.get("/dashboard/inbox")
    assert "nicht zugeordnet" in response.text
    assert "Betriebspruefung angekuendigt" in response.text


def test_inbox_marks_outbound_message(client: TestClient, seeded: dict) -> None:
    response = client.get("/dashboard/inbox")
    assert "ausgehend" in response.text


# --- Filter ---


def test_unmatched_filter_excludes_matched_message(
    client: TestClient, seeded: dict
) -> None:
    response = client.get("/dashboard/inbox", params={"filter": "unmatched"})
    assert response.status_code == 200
    assert "Betriebspruefung angekuendigt" in response.text
    assert "Steuerbescheid 2025 - Einspruchsfrist beachten" not in response.text


def test_outbound_filter_shows_only_outbound(client: TestClient, seeded: dict) -> None:
    response = client.get("/dashboard/inbox", params={"filter": "outbound"})
    assert response.status_code == 200
    assert "RE: Steuerbescheid 2025" in response.text
    assert "Betriebspruefung angekuendigt" not in response.text


def test_unknown_filter_value_falls_back_to_all(
    client: TestClient, seeded: dict
) -> None:
    """Ein manipulierter/unbekannter Filter-Query-Parameter darf hoechstens
    auf 'alle Nachrichten' zurueckfallen, nie zu einem Serverfehler
    fuehren."""
    response = client.get("/dashboard/inbox", params={"filter": "__hack__"})
    assert response.status_code == 200
    assert "Betriebspruefung angekuendigt" in response.text
    assert "Steuerbescheid 2025 - Einspruchsfrist beachten" in response.text


def test_inbox_list_partial_returns_only_fragment(
    client: TestClient, seeded: dict
) -> None:
    """HTMX-Partial-Endpunkt liefert nur die Liste, keine volle Seite (kein
    <html>/<nav>-Grundgeruest)."""
    response = client.get("/dashboard/inbox/list", params={"filter": "all"})
    assert response.status_code == 200
    assert "<html" not in response.text
    assert 'id="message-list"' in response.text


# --- Detailansicht ---


def test_inbox_message_page_shows_detail_and_document(
    client: TestClient, seeded: dict
) -> None:
    response = client.get(f"/dashboard/inbox/{seeded['matched_message_id']}")
    assert response.status_code == 200
    assert "steuerbescheid_2025_test.pdf" in response.text
    assert "steuerbescheid" in response.text


def test_inbox_message_detail_partial_returns_only_fragment(
    client: TestClient, seeded: dict
) -> None:
    response = client.get(
        f"/dashboard/inbox/{seeded['matched_message_id']}/detail"
    )
    assert response.status_code == 200
    assert "<html" not in response.text
    assert 'id="detail-pane"' in response.text


def test_detail_response_excludes_internal_file_path(
    client: TestClient, seeded: dict
) -> None:
    """Dieselbe Allowlist-Grundregel wie bei der JSON-API (Prompt 21): der
    interne Ablagepfad darf nicht im HTML landen."""
    response = client.get(f"/dashboard/inbox/{seeded['matched_message_id']}")
    assert "/data/intake/test/" not in response.text


def test_unmatched_message_detail_shows_unmatched_badge_not_matter(
    client: TestClient, seeded: dict
) -> None:
    response = client.get(
        f"/dashboard/inbox/{seeded['unmatched_message_id']}/detail"
    )
    assert response.status_code == 200
    assert "nicht zugeordnet" in response.text


def test_message_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/dashboard/inbox/does-not-exist")
    assert response.status_code == 404


def test_message_detail_partial_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/dashboard/inbox/does-not-exist/detail")
    assert response.status_code == 404


# --- Sidebar / ehrliche Darstellung des Entwicklungsstands ---


def test_sidebar_shows_all_eight_areas(client: TestClient, seeded: dict) -> None:
    response = client.get("/dashboard/inbox")
    for label in [
        "Dashboard",
        "Posteingang",
        "Akten",
        "Entwürfe zur Prüfung",
        "Rechtsquellen",
        "Kanzlei-Wissen",
        "Postausgang",
        "Einstellungen",
    ]:
        assert label in response.text


def test_sidebar_marks_unbuilt_areas_as_not_clickable(
    client: TestClient, seeded: dict
) -> None:
    """Nur 'Posteingang' ist als echter Link (<a href>) vorhanden - alle
    anderen Bereiche sind bewusst nicht verlinkt (kein toter Link, der
    404 werfen wuerde), siehe base.html."""
    response = client.get("/dashboard/inbox")
    assert 'href="/dashboard/inbox"' in response.text
    assert "sidebar__link--disabled" in response.text
