"""Tests fuer das FastAPI-Backend (Prompt 21).

Nutzt eine geteilte In-Memory-SQLite-Datenbank ueber `app.dependency_overrides`
- FastAPI fuehrt synchrone Endpunkte in einem Thread-Pool aus, und eine
SQLite-In-Memory-Datenbank ist normalerweise NUR innerhalb derselben
Connection sichtbar. Ohne `poolclass=StaticPool` wuerde jeder Thread eine
eigene, leere Datenbank sehen ("no such table") - echter Bug, der waehrend
der Entwicklung dieses Prompts gefunden wurde.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import (
    AuditEvent,
    Client,
    Deadline,
    Document,
    Draft,
    KnowledgeItem,
    Matter,
    Message,
    Source,
    Task,
)
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
        # Prompt 26: /api/... erfordert eine gueltige Session - Admin
        # deckt alle Berechtigungen ab, veraendert die eigentlich
        # getestete (Prompt-21-)Fachlogik dieser Datei also nicht.
        login_as_admin(db_session, test_client)
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def seeded(db_session: Session) -> dict[str, str]:
    """Legt einen durchgaengigen, synthetischen Datensatz an: Mandant ->
    Akte -> Nachricht/Dokument/Entwurf/Aufgabe/Frist/Audit-Event, plus
    eine kanzleiweite Quelle und ein Wissenselement. Ausschliesslich
    synthetische Testdaten - keine echten Mandantendaten (Grundregel)."""
    mandant = Client(name="Synthetischer Testmandant GmbH")
    db_session.add(mandant)
    db_session.flush()

    matter = Matter(client_id=mandant.id, title="Einspruch Steuerbescheid 2025")
    db_session.add(matter)
    db_session.flush()

    unmatched_message = Message(
        matter_id=None,
        direction="inbound",
        sender="mandant@example-testdomain.invalid",
        subject="Neuer Steuerbescheid erhalten",
        body_text="Testinhalt, keine echten Mandantendaten.",
    )
    matched_message = Message(
        matter_id=matter.id,
        direction="inbound",
        sender="mandant@example-testdomain.invalid",
        subject="Rueckfrage zur Frist",
        body_text="Testinhalt.",
    )
    db_session.add_all([unmatched_message, matched_message])
    db_session.flush()

    document = Document(
        matter_id=matter.id,
        message_id=matched_message.id,
        original_filename="steuerbescheid_test.pdf",
        file_path="/data/intake/test/steuerbescheid_test.pdf",
        classified_type="steuerbescheid",
        classification_confidence=0.4,
    )
    draft = Draft(matter_id=matter.id, content="Sehr geehrte Damen und Herren, ...")
    task = Task(matter_id=matter.id, title="Einspruchsfrist pruefen")
    deadline = Deadline(
        matter_id=matter.id,
        source_text="Einspruch ist innerhalb eines Monats einzulegen.",
        due_date=date(2026, 9, 30),
        confidence=0.5,
        reasoning="Regelbasiert erkannt - NICHT als verbindlich bestätigt, manuelle Prüfung erforderlich.",
    )
    source = Source(
        title="AO § 355 Einspruchsfrist",
        source_type="Gesetz",
        approval_level="freigegeben",
    )
    knowledge_item = KnowledgeItem(
        title="Standard-Textbaustein Einspruch",
        content="Testinhalt eines Textbausteins.",
        approval_status="approved",
    )
    db_session.add_all([document, draft, task, deadline, source, knowledge_item])
    db_session.flush()

    audit_event = AuditEvent(
        entity_type="Document",
        entity_id=document.id,
        event_type="document_classified",
        actor="system",
        details="Testklassifikation.",
    )
    db_session.add(audit_event)
    db_session.commit()

    return {
        "client_id": mandant.id,
        "matter_id": matter.id,
        "unmatched_message_id": unmatched_message.id,
        "matched_message_id": matched_message.id,
        "document_id": document.id,
        "draft_id": draft.id,
        "task_id": task.id,
        "deadline_id": deadline.id,
        "source_id": source.id,
        "knowledge_item_id": knowledge_item.id,
    }


# --- Inbox ---


def test_list_inbox_returns_all_messages(client: TestClient, seeded: dict) -> None:
    response = client.get("/api/inbox")
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert seeded["unmatched_message_id"] in ids
    assert seeded["matched_message_id"] in ids


def test_list_inbox_unmatched_only_excludes_matched_message(
    client: TestClient, seeded: dict
) -> None:
    response = client.get("/api/inbox", params={"unmatched_only": True})
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert seeded["unmatched_message_id"] in ids
    assert seeded["matched_message_id"] not in ids


def test_list_inbox_filtered_by_matter(client: TestClient, seeded: dict) -> None:
    response = client.get("/api/inbox", params={"matter_id": seeded["matter_id"]})
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert ids == {seeded["matched_message_id"]}


def test_get_inbox_message_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/api/inbox/does-not-exist")
    assert response.status_code == 404


# --- Akten ---


def test_list_matters_returns_seeded_matter(client: TestClient, seeded: dict) -> None:
    response = client.get("/api/matters")
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert seeded["matter_id"] in ids


def test_get_matter_by_id(client: TestClient, seeded: dict) -> None:
    response = client.get(f"/api/matters/{seeded['matter_id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Einspruch Steuerbescheid 2025"


def test_get_matter_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/api/matters/does-not-exist")
    assert response.status_code == 404


# --- Dokumente ---


def test_list_documents_filtered_by_matter(client: TestClient, seeded: dict) -> None:
    response = client.get("/api/documents", params={"matter_id": seeded["matter_id"]})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == seeded["document_id"]


def test_document_response_excludes_internal_file_path(
    client: TestClient, seeded: dict
) -> None:
    """Sichert die Allowlist ab: `file_path` (interner Ablagepfad) darf
    nicht ueber die API sichtbar sein."""
    response = client.get(f"/api/documents/{seeded['document_id']}")
    assert response.status_code == 200
    assert "file_path" not in response.json()


# --- Entwuerfe ---


def test_list_drafts_filtered_by_matter(client: TestClient, seeded: dict) -> None:
    response = client.get("/api/drafts", params={"matter_id": seeded["matter_id"]})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == seeded["draft_id"]
    assert body[0]["status"] == "draft"


def test_list_drafts_filtered_by_status_excludes_non_matching(
    client: TestClient, seeded: dict
) -> None:
    response = client.get("/api/drafts", params={"status": "approved"})
    assert response.status_code == 200
    assert response.json() == []


# --- Quellen ---


def test_list_sources_filtered_by_approval_level(
    client: TestClient, seeded: dict
) -> None:
    response = client.get("/api/sources", params={"approval_level": "freigegeben"})
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert seeded["source_id"] in ids


def test_list_sources_wrong_approval_level_excludes_source(
    client: TestClient, seeded: dict
) -> None:
    response = client.get("/api/sources", params={"approval_level": "entwurf"})
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert seeded["source_id"] not in ids


# --- Kanzlei-Wissen ---


def test_list_knowledge_items_filtered_by_approval_status(
    client: TestClient, seeded: dict
) -> None:
    response = client.get("/api/knowledge", params={"approval_status": "approved"})
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert seeded["knowledge_item_id"] in ids


# --- Aufgaben / Fristen ---


def test_list_tasks_filtered_by_matter(client: TestClient, seeded: dict) -> None:
    response = client.get("/api/tasks", params={"matter_id": seeded["matter_id"]})
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert seeded["task_id"] in ids


def test_list_deadlines_never_shown_as_confirmed_by_default(
    client: TestClient, seeded: dict
) -> None:
    """Grundregel Prompt 10: eine erkannte Frist darf nie implizit als
    bestaetigt gelten. Prueft, dass der API-Response-Status unveraendert
    'unreviewed' bleibt."""
    response = client.get("/api/deadlines", params={"matter_id": seeded["matter_id"]})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["review_status"] == "unreviewed"


def test_list_deadlines_filtered_by_review_status(
    client: TestClient, seeded: dict
) -> None:
    response = client.get("/api/deadlines", params={"review_status": "confirmed"})
    assert response.status_code == 200
    assert response.json() == []


def test_deadline_response_includes_reasoning(client: TestClient, seeded: dict) -> None:
    """Strukturierte, maschinenlesbare Ausgabe muss die Begruendung
    enthalten, warum eine erkannte Frist nicht als verbindlich gilt - siehe
    app/models/deadline.py::Deadline.reasoning."""
    response = client.get("/api/deadlines", params={"matter_id": seeded["matter_id"]})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "NICHT als verbindlich bestätigt" in body[0]["reasoning"]


def test_get_single_deadline_includes_reasoning(client: TestClient, seeded: dict) -> None:
    response = client.get(f"/api/deadlines/{seeded['deadline_id']}")
    assert response.status_code == 200
    assert response.json()["reasoning"] is not None


# --- Einstellungen ---


def test_settings_endpoint_does_not_leak_mail_password(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import get_settings

    monkeypatch.setenv("MAIL_PASSWORD", "super-geheimes-test-passwort")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-geheim-00000000")
    get_settings.cache_clear()
    # cache_clear() erzeugt beim naechsten Zugriff eine NEUE Settings-
    # Instanz - im Entwicklungsmodus mit einem NEUEN zufaelligen
    # Session-Secret (siehe resolved_session_secret_key), wodurch die
    # bereits ausgestellte Session-Cookie ungueltig wird. Erneuter Login
    # noetig, damit die Cookie mit dem NEUEN Secret signiert ist.
    login_as_admin(db_session, client, email="admin-reauth@kanzlei.test")
    try:
        response = client.get("/api/settings")
        assert response.status_code == 200
        raw_body = response.text
        assert "super-geheimes-test-passwort" not in raw_body
        assert "sk-ant-test-geheim-00000000" not in raw_body
        assert "mail_password" not in raw_body
        assert "anthropic_api_key" not in raw_body
    finally:
        get_settings.cache_clear()


def test_settings_endpoint_returns_safe_fields(client: TestClient) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["app_env"] == "development"
    assert body["database_url_kind"] == "sqlite"
    assert "require_human_approval_before_send" in body


# --- Audit ---


def test_list_audit_events_for_matter_includes_document_event(
    client: TestClient, seeded: dict
) -> None:
    response = client.get(f"/api/audit/matter/{seeded['matter_id']}")
    assert response.status_code == 200
    event_types = {item["event_type"] for item in response.json()}
    assert "document_classified" in event_types


def test_list_audit_events_for_entity(client: TestClient, seeded: dict) -> None:
    response = client.get(f"/api/audit/entity/Document/{seeded['document_id']}")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["actor"] == "system"


# --- Pagination / allgemeine Validierung ---


def test_limit_parameter_is_enforced(client: TestClient, seeded: dict) -> None:
    response = client.get("/api/matters", params={"limit": 0})
    assert response.status_code == 422


def test_authentication_now_required_since_prompt_26(
    client: TestClient, seeded: dict
) -> None:
    """Ersetzt den bis Prompt 25 gültigen Test (Konzept Prompt 21: 'noch
    keine Produktionsauthentifizierung') - seit Prompt 26 gilt das
    Gegenteil: /api/... erfordert immer eine gültige Session. `client`
    ist hier bereits eingeloggt (siehe Fixture) - dieser Test bestätigt
    nur, dass der eingeloggte Zugriff funktioniert; die Verweigerung ohne
    Login wird ausführlich in tests/test_auth_web.py geprüft."""
    response = client.get("/api/matters")
    assert response.status_code == 200
