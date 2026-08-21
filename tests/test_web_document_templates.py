"""Tests für app/web/document_templates_router.py (Kanzlei-Mustertexte,
Block 3, 20.08.) - löst den bisherigen Platzhalter unter
`/dashboard/library/mustertexte` ab."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import DocumentTemplate
from app.models.base import Base
from tests.auth_test_utils import create_test_user, extract_csrf, login, login_as_admin, seed_roles


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
def mitarbeiter_client(db_session: Session) -> Iterator[TestClient]:
    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        test_client = TestClient(app)
        roles = seed_roles(db_session)
        create_test_user(db_session, roles["mitarbeiter"], "mitarbeiter@kanzlei.test")
        login(test_client, "mitarbeiter@kanzlei.test")
        yield test_client
    finally:
        app.dependency_overrides.clear()


def _csrf(test_client: TestClient, path: str = "/dashboard/library/mustertexte") -> str:
    return extract_csrf(test_client.get(path).text)


def test_page_is_no_longer_a_placeholder(client: TestClient) -> None:
    response = client.get("/dashboard/library/mustertexte")
    assert response.status_code == 200
    assert "in Vorbereitung" not in response.text
    assert "Kanzlei-Mustertexte" in response.text


def test_page_shows_placeholder_reference(client: TestClient) -> None:
    response = client.get("/dashboard/library/mustertexte")
    assert "[Mandantenname]" in response.text
    assert "[Paragraf:BGB" in response.text


def test_create_template_as_admin_succeeds(client: TestClient, db_session: Session) -> None:
    csrf_token = _csrf(client)
    response = client.post(
        "/dashboard/library/mustertexte",
        data={
            "csrf_token": csrf_token,
            "name": "Mahnung Standard",
            "category": "Mahnung",
            "description": "",
            "content": "Sehr geehrte/r [Mandantenname]",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert db_session.query(DocumentTemplate).filter_by(name="Mahnung Standard").count() == 1


def test_create_template_as_mitarbeiter_is_forbidden(mitarbeiter_client: TestClient) -> None:
    csrf_token = _csrf(mitarbeiter_client)
    response = mitarbeiter_client.post(
        "/dashboard/library/mustertexte",
        data={"csrf_token": csrf_token, "name": "Verboten", "content": "x"},
    )
    assert response.status_code == 403


def test_mitarbeiter_can_read_template_list(mitarbeiter_client: TestClient) -> None:
    response = mitarbeiter_client.get("/dashboard/library/mustertexte")
    assert response.status_code == 200
    assert "Bearbeiten" not in response.text  # kein Curator-Aktionslink


def test_edit_page_forbidden_for_mitarbeiter(
    mitarbeiter_client: TestClient, db_session: Session
) -> None:
    template = DocumentTemplate(name="Vorlage", content="x", version=1)
    db_session.add(template)
    db_session.commit()
    response = mitarbeiter_client.get(f"/dashboard/library/mustertexte/{template.id}/edit")
    assert response.status_code == 403


def test_update_template_increments_version(client: TestClient, db_session: Session) -> None:
    template = DocumentTemplate(name="Alt", content="Alter Text", version=1)
    db_session.add(template)
    db_session.commit()

    csrf_token = _csrf(client, f"/dashboard/library/mustertexte/{template.id}/edit")
    response = client.post(
        f"/dashboard/library/mustertexte/{template.id}",
        data={"csrf_token": csrf_token, "name": "Neu", "category": "", "description": "", "content": "Neuer Text"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db_session.refresh(template)
    assert template.name == "Neu"
    assert template.version == 2


def test_delete_unused_template_succeeds(client: TestClient, db_session: Session) -> None:
    template = DocumentTemplate(name="Loeschbar", content="x", version=1)
    db_session.add(template)
    db_session.commit()

    csrf_token = _csrf(client)
    response = client.post(
        f"/dashboard/library/mustertexte/{template.id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert db_session.get(DocumentTemplate, template.id) is None


def test_unauthenticated_cannot_view_page(db_session: Session) -> None:
    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        anon = TestClient(app)
        response = anon.get("/dashboard/library/mustertexte", follow_redirects=False)
        assert response.status_code == 303
        assert "/dashboard/login" in response.headers["location"]
    finally:
        app.dependency_overrides.clear()
