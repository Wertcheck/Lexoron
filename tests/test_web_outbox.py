"""Tests für app/web/outbox_router.py und die Integration mit
`approve_draft` in app/web/drafts_router.py (Prompt 25, Auth ab Prompt 26).
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
from app.models import Client, Draft, Matter, OutboxEntry
from app.models.base import Base
from tests.auth_test_utils import extract_csrf, login_as_admin


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
    client_ = Client(name="Synthetischer Testmandant GmbH")
    matter = Matter(client=client_, title="Einspruch Steuerbescheid 2025")
    draft = Draft(matter=matter, content="Freigegebener Entwurfstext.")
    db_session.add_all([client_, matter, draft])
    db_session.commit()
    return {"matter_id": matter.id, "draft_id": draft.id}


def _draft_csrf(client: TestClient, draft_id: str) -> str:
    return extract_csrf(client.get(f"/dashboard/drafts/{draft_id}").text)


# --- Integration: Freigeben uebergibt automatisch in den Postausgang ---


def test_approve_creates_outbox_entry(
    client: TestClient, db_session: Session, seeded: dict
) -> None:
    csrf = _draft_csrf(client, seeded["draft_id"])
    client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/approve",
        data={"csrf_token": csrf},
    )
    entries = db_session.query(OutboxEntry).filter_by(draft_id=seeded["draft_id"]).all()
    assert len(entries) == 1
    assert entries[0].status == "pending"


def test_approving_twice_does_not_duplicate_outbox_entry(
    client: TestClient, db_session: Session, seeded: dict
) -> None:
    csrf1 = _draft_csrf(client, seeded["draft_id"])
    client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/approve",
        data={"csrf_token": csrf1},
    )
    csrf2 = _draft_csrf(client, seeded["draft_id"])
    response = client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/approve",
        data={"csrf_token": csrf2},
        follow_redirects=False,
    )
    assert response.status_code == 303  # kein 500, kein Crash
    entries = db_session.query(OutboxEntry).filter_by(draft_id=seeded["draft_id"]).all()
    assert len(entries) == 1


def test_rejected_draft_gets_no_outbox_entry(
    client: TestClient, db_session: Session, seeded: dict
) -> None:
    csrf = _draft_csrf(client, seeded["draft_id"])
    client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/reject",
        data={"comment": "Nicht ausreichend.", "csrf_token": csrf},
    )
    assert db_session.query(OutboxEntry).count() == 0


# --- Listenansicht ---


def test_outbox_list_returns_200(client: TestClient) -> None:
    response = client.get("/dashboard/outbox")
    assert response.status_code == 200


def test_outbox_list_shows_pending_entry(
    client: TestClient, db_session: Session, seeded: dict
) -> None:
    csrf = _draft_csrf(client, seeded["draft_id"])
    client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/approve",
        data={"csrf_token": csrf},
    )
    response = client.get("/dashboard/outbox")
    assert "Einspruch Steuerbescheid 2025" in response.text
    assert "pending" in response.text


def test_outbox_list_default_excludes_sent(
    client: TestClient, db_session: Session, seeded: dict
) -> None:
    csrf = _draft_csrf(client, seeded["draft_id"])
    client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/approve",
        data={"csrf_token": csrf},
    )
    entry = db_session.query(OutboxEntry).filter_by(draft_id=seeded["draft_id"]).first()
    outbox_csrf = _draft_csrf(client, seeded["draft_id"])
    client.post(
        f"/dashboard/outbox/{entry.id}/mark-sent", data={"csrf_token": outbox_csrf}
    )

    response = client.get("/dashboard/outbox")
    assert "Einspruch Steuerbescheid 2025" not in response.text

    response_sent = client.get("/dashboard/outbox", params={"status": "sent"})
    assert "Einspruch Steuerbescheid 2025" in response_sent.text


def test_outbox_list_explains_no_automatic_sending(client: TestClient) -> None:
    response = client.get("/dashboard/outbox")
    assert "versendet nichts automatisch" in response.text


# --- Als versendet markieren ---


def test_mark_sent_updates_status_and_redirects(
    client: TestClient, db_session: Session, seeded: dict
) -> None:
    csrf = _draft_csrf(client, seeded["draft_id"])
    client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/approve",
        data={"csrf_token": csrf},
    )
    entry = db_session.query(OutboxEntry).filter_by(draft_id=seeded["draft_id"]).first()

    outbox_csrf = _draft_csrf(client, seeded["draft_id"])
    response = client.post(
        f"/dashboard/outbox/{entry.id}/mark-sent",
        data={"csrf_token": outbox_csrf},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard/outbox"
    db_session.expire_all()
    reloaded = db_session.get(OutboxEntry, entry.id)
    assert reloaded.status == "sent"
    assert reloaded.sent_by == "admin@kanzlei.test"


def test_mark_sent_not_found_returns_404(client: TestClient, seeded: dict) -> None:
    outbox_csrf = _draft_csrf(client, seeded["draft_id"])
    response = client.post(
        "/dashboard/outbox/does-not-exist/mark-sent", data={"csrf_token": outbox_csrf}
    )
    assert response.status_code == 404


def test_mark_sent_twice_shows_friendly_error_instead_of_crashing(
    client: TestClient, db_session: Session, seeded: dict
) -> None:
    """Ein zweiter Versuch, denselben Eintrag als versendet zu markieren
    (z. B. Doppelklick, zwei parallel geöffnete Tabs), darf NICHT zu
    einem Serverfehler führen - sauberer Redirect mit Fehlermeldung."""
    csrf = _draft_csrf(client, seeded["draft_id"])
    client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/approve",
        data={"csrf_token": csrf},
    )
    entry = db_session.query(OutboxEntry).filter_by(draft_id=seeded["draft_id"]).first()
    first_csrf = _draft_csrf(client, seeded["draft_id"])
    client.post(f"/dashboard/outbox/{entry.id}/mark-sent", data={"csrf_token": first_csrf})

    second_csrf = _draft_csrf(client, seeded["draft_id"])
    response = client.post(
        f"/dashboard/outbox/{entry.id}/mark-sent",
        data={"csrf_token": second_csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=" in response.headers["location"]

    db_session.expire_all()
    reloaded = db_session.get(OutboxEntry, entry.id)
    assert reloaded.sent_by == "admin@kanzlei.test"  # unveraendert vom ersten Versuch
