"""Tests für app/web/document_generator_router.py (Dokumentengenerator,
Block 3, 20.08.), unter /dashboard/tools/dokumentgenerator."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Client, DocumentTemplate, GeneratedDocument, Matter
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


def _csrf(test_client: TestClient, path: str = "/dashboard/tools/dokumentgenerator") -> str:
    return extract_csrf(test_client.get(path).text)


def _seed_matter_and_template(db: Session) -> tuple[Matter, DocumentTemplate]:
    client_row = Client(name="Muster GmbH", client_number="M-1")
    db.add(client_row)
    db.flush()
    matter = Matter(client_id=client_row.id, title="Testakte", status="open", reference_number="AZ-1")
    db.add(matter)
    template = DocumentTemplate(
        name="Testvorlage", content="Sehr geehrte/r [Mandantenname], Az. [Aktenzeichen].", version=1
    )
    db.add(template)
    db.commit()
    db.refresh(matter)
    db.refresh(template)
    return matter, template


# --- Zugriff ---


def test_generator_requires_login(db_session: Session) -> None:
    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        anon = TestClient(app)
        response = anon.get("/dashboard/tools/dokumentgenerator", follow_redirects=False)
        assert response.status_code == 303
        assert "/dashboard/login" in response.headers["location"]
    finally:
        app.dependency_overrides.clear()


# --- Picker-Seite ---


def test_generator_page_is_not_a_placeholder(client: TestClient) -> None:
    response = client.get("/dashboard/tools/dokumentgenerator")
    assert response.status_code == 200
    assert "in Vorbereitung" not in response.text
    assert "Dokumentengenerator" in response.text


def test_generator_page_lists_templates_and_matters(client: TestClient, db_session: Session) -> None:
    matter, template = _seed_matter_and_template(db_session)
    response = client.get("/dashboard/tools/dokumentgenerator")
    assert "Testvorlage" in response.text
    assert "Testakte" in response.text


def test_generator_page_preselects_matter_from_query_param(
    client: TestClient, db_session: Session
) -> None:
    matter, _template = _seed_matter_and_template(db_session)
    response = client.get("/dashboard/tools/dokumentgenerator", params={"matter_id": matter.id})
    assert f'value="{matter.id}" selected' in response.text


# --- Generieren ---


def test_generate_creates_document_and_redirects_to_review(
    client: TestClient, db_session: Session
) -> None:
    matter, template = _seed_matter_and_template(db_session)
    csrf_token = _csrf(client)
    response = client.post(
        "/dashboard/tools/dokumentgenerator/generate",
        data={"csrf_token": csrf_token, "template_id": template.id, "matter_id": matter.id},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/dashboard/tools/dokumentgenerator/")

    detail = client.get(response.headers["location"])
    assert "Muster GmbH" in detail.text
    assert "AZ-1" in detail.text


def test_generate_with_unknown_template_shows_error(client: TestClient, db_session: Session) -> None:
    matter, _template = _seed_matter_and_template(db_session)
    csrf_token = _csrf(client)
    response = client.post(
        "/dashboard/tools/dokumentgenerator/generate",
        data={"csrf_token": csrf_token, "template_id": "does-not-exist", "matter_id": matter.id},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=" in response.headers["location"]


# --- Vorschau/Bearbeiten ---


def test_review_page_shows_unresolved_placeholder_warning(
    client: TestClient, db_session: Session
) -> None:
    client_row = Client(name="Muster GmbH", client_number="M-2")
    db_session.add(client_row)
    db_session.flush()
    matter = Matter(client_id=client_row.id, title="Akte ohne Aktenzeichen", status="open")
    db_session.add(matter)
    template = DocumentTemplate(name="Vorlage", content="Az. [Aktenzeichen]", version=1)
    db_session.add(template)
    db_session.commit()

    csrf_token = _csrf(client)
    response = client.post(
        "/dashboard/tools/dokumentgenerator/generate",
        data={"csrf_token": csrf_token, "template_id": template.id, "matter_id": matter.id},
        follow_redirects=True,
    )
    assert "konnte" in response.text or "konnten" in response.text
    assert "[Aktenzeichen]" in response.text


def test_save_updates_document_content(client: TestClient, db_session: Session) -> None:
    matter, template = _seed_matter_and_template(db_session)
    csrf_token = _csrf(client)
    gen_response = client.post(
        "/dashboard/tools/dokumentgenerator/generate",
        data={"csrf_token": csrf_token, "template_id": template.id, "matter_id": matter.id},
        follow_redirects=False,
    )
    document_id = gen_response.headers["location"].rsplit("/", 1)[-1]

    csrf_token = _csrf(client, f"/dashboard/tools/dokumentgenerator/{document_id}")
    client.post(
        f"/dashboard/tools/dokumentgenerator/{document_id}/save",
        data={"csrf_token": csrf_token, "content": "Manuell geänderter Text."},
        follow_redirects=False,
    )
    document = db_session.get(GeneratedDocument, document_id)
    assert document.content == "Manuell geänderter Text."


def test_review_unknown_document_returns_404(client: TestClient) -> None:
    response = client.get("/dashboard/tools/dokumentgenerator/does-not-exist")
    assert response.status_code == 404


# --- Export ---


def test_export_docx_returns_downloadable_file(client: TestClient, db_session: Session) -> None:
    matter, template = _seed_matter_and_template(db_session)
    csrf_token = _csrf(client)
    gen_response = client.post(
        "/dashboard/tools/dokumentgenerator/generate",
        data={"csrf_token": csrf_token, "template_id": template.id, "matter_id": matter.id},
        follow_redirects=False,
    )
    document_id = gen_response.headers["location"].rsplit("/", 1)[-1]

    csrf_token = _csrf(client, f"/dashboard/tools/dokumentgenerator/{document_id}")
    response = client.post(
        f"/dashboard/tools/dokumentgenerator/{document_id}/export/docx",
        data={"csrf_token": csrf_token},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert response.content[:2] == b"PK"  # DOCX ist ein ZIP-Container


def test_export_pdf_returns_downloadable_file(client: TestClient, db_session: Session) -> None:
    matter, template = _seed_matter_and_template(db_session)
    csrf_token = _csrf(client)
    gen_response = client.post(
        "/dashboard/tools/dokumentgenerator/generate",
        data={"csrf_token": csrf_token, "template_id": template.id, "matter_id": matter.id},
        follow_redirects=False,
    )
    document_id = gen_response.headers["location"].rsplit("/", 1)[-1]

    csrf_token = _csrf(client, f"/dashboard/tools/dokumentgenerator/{document_id}")
    response = client.post(
        f"/dashboard/tools/dokumentgenerator/{document_id}/export/pdf",
        data={"csrf_token": csrf_token},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"


# --- Aktenisolation ---


def test_generated_document_only_contains_data_from_its_own_matter(
    client: TestClient, db_session: Session
) -> None:
    client_a = Client(name="Mandant A", client_number="A-1")
    client_b = Client(name="Mandant B", client_number="B-1")
    db_session.add_all([client_a, client_b])
    db_session.flush()
    matter_a = Matter(client_id=client_a.id, title="Akte A", status="open")
    matter_b = Matter(client_id=client_b.id, title="Akte B", status="open")
    db_session.add_all([matter_a, matter_b])
    template = DocumentTemplate(name="Vorlage", content="[Mandantenname]", version=1)
    db_session.add(template)
    db_session.commit()

    csrf_token = _csrf(client)
    response = client.post(
        "/dashboard/tools/dokumentgenerator/generate",
        data={"csrf_token": csrf_token, "template_id": template.id, "matter_id": matter_a.id},
        follow_redirects=True,
    )
    assert "Mandant A" in response.text
    assert "Mandant B" not in response.text
