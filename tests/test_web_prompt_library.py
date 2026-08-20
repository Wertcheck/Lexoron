"""Tests für /dashboard/library/prompts (Schritt 3, Teil 2): Standard-
Prompts-Bibliothek - read-only System-Prompt-Referenz + editierbare
Kanzlei-Prompts."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import PromptTemplate
from app.models.base import Base
from tests.auth_test_utils import create_test_user, extract_csrf, login, seed_roles


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


def test_unauthenticated_access_is_denied(client: TestClient) -> None:
    response = client.get("/dashboard/library/prompts", follow_redirects=False)
    assert response.status_code == 303
    assert "/dashboard/login" in response.headers["location"]


def test_page_shows_real_system_prompts(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")

    response = client.get("/dashboard/library/prompts")

    assert response.status_code == 200
    from app.ai_providers.claude_writing_provider import WRITING_SYSTEM_PROMPT

    # Ein charakteristischer Ausschnitt des echten Systemprompts muss
    # wortwoertlich erscheinen - beweist, dass die Seite den TATSAECHLICHEN
    # Text zeigt, nicht eine separat gepflegte (potenziell veraltete) Kopie.
    assert "sprachlichen Formulierung eines Antwortschreibens" in response.text
    assert WRITING_SYSTEM_PROMPT.splitlines()[0].strip() in response.text


def test_mitarbeiter_cannot_create_template(
    client: TestClient, db_session: Session, roles
) -> None:
    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")
    page = client.get("/dashboard/library/prompts")
    csrf = extract_csrf(page.text)

    response = client.post(
        "/dashboard/library/prompts",
        data={"csrf_token": csrf, "name": "Testvorlage", "content": "Text {Mandant}"},
    )

    assert response.status_code == 403
    assert db_session.query(PromptTemplate).count() == 0


def test_anwalt_can_create_template(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["anwalt"], "anwalt@kanzlei.test")
    login(client, "anwalt@kanzlei.test")
    page = client.get("/dashboard/library/prompts")
    csrf = extract_csrf(page.text)

    response = client.post(
        "/dashboard/library/prompts",
        data={
            "csrf_token": csrf,
            "name": "Fristverlängerung",
            "content": "Sehr geehrte/r {Mandant}, Frist: {Frist}.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    template = db_session.query(PromptTemplate).first()
    assert template is not None
    assert template.name == "Fristverlängerung"
    assert template.created_by_actor == "anwalt@kanzlei.test"


def test_blank_content_is_rejected(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["admin"], "admin@kanzlei.test")
    login(client, "admin@kanzlei.test")
    page = client.get("/dashboard/library/prompts")
    csrf = extract_csrf(page.text)

    response = client.post(
        "/dashboard/library/prompts",
        data={"csrf_token": csrf, "name": "Leer", "content": "   "},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert db_session.query(PromptTemplate).count() == 0


def _create_template(client: TestClient, csrf: str) -> str:
    client.post(
        "/dashboard/library/prompts",
        data={
            "csrf_token": csrf,
            "name": "Fristverlängerung",
            "content": "Sehr geehrte/r {Mandant}, Frist: {Frist}.",
        },
    )


def test_edit_updates_content_and_increments_version(
    client: TestClient, db_session: Session, roles
) -> None:
    create_test_user(db_session, roles["admin"], "admin@kanzlei.test")
    login(client, "admin@kanzlei.test")
    page = client.get("/dashboard/library/prompts")
    csrf = extract_csrf(page.text)
    _create_template(client, csrf)
    template = db_session.query(PromptTemplate).first()

    response = client.post(
        f"/dashboard/library/prompts/{template.id}",
        data={
            "csrf_token": csrf,
            "name": "Fristverlängerung (neu)",
            "content": "Geänderter Text {Mandant}",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    db_session.refresh(template)
    assert template.name == "Fristverlängerung (neu)"
    assert template.version == 2


def test_mitarbeiter_cannot_reach_edit_page(
    client: TestClient, db_session: Session, roles
) -> None:
    create_test_user(db_session, roles["admin"], "admin@kanzlei.test")
    login(client, "admin@kanzlei.test")
    page = client.get("/dashboard/library/prompts")
    csrf = extract_csrf(page.text)
    _create_template(client, csrf)
    template = db_session.query(PromptTemplate).first()
    client.post("/dashboard/logout", data={"csrf_token": csrf})

    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")

    response = client.get(f"/dashboard/library/prompts/{template.id}/edit")
    assert response.status_code == 403


def test_delete_removes_template(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["admin"], "admin@kanzlei.test")
    login(client, "admin@kanzlei.test")
    page = client.get("/dashboard/library/prompts")
    csrf = extract_csrf(page.text)
    _create_template(client, csrf)
    template = db_session.query(PromptTemplate).first()

    response = client.post(
        f"/dashboard/library/prompts/{template.id}/delete",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert db_session.query(PromptTemplate).count() == 0


def test_mitarbeiter_can_render_preview(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["admin"], "admin@kanzlei.test")
    login(client, "admin@kanzlei.test")
    page = client.get("/dashboard/library/prompts")
    csrf = extract_csrf(page.text)
    _create_template(client, csrf)
    template = db_session.query(PromptTemplate).first()
    client.post("/dashboard/logout", data={"csrf_token": csrf})

    create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
    login(client, "mitarbeiter@kanzlei.test")
    page = client.get("/dashboard/library/prompts")
    csrf = extract_csrf(page.text)

    response = client.post(
        f"/dashboard/library/prompts/{template.id}/render",
        data={"csrf_token": csrf, "Mandant": "Max Mustermann", "Frist": "01.01.2027"},
    )

    assert response.status_code == 200
    assert "Max Mustermann" in response.text
    assert "01.01.2027" in response.text


def test_render_leaves_missing_variable_untouched(
    client: TestClient, db_session: Session, roles
) -> None:
    create_test_user(db_session, roles["admin"], "admin@kanzlei.test")
    login(client, "admin@kanzlei.test")
    page = client.get("/dashboard/library/prompts")
    csrf = extract_csrf(page.text)
    _create_template(client, csrf)
    template = db_session.query(PromptTemplate).first()

    response = client.post(
        f"/dashboard/library/prompts/{template.id}/render",
        data={"csrf_token": csrf, "Mandant": "Max Mustermann"},
    )

    assert "Max Mustermann" in response.text
    assert "{Frist}" in response.text
