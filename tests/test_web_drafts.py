"""Tests für app/web/drafts_router.py (Prompt 23).

Gleiches Testmuster wie tests/test_web_inbox.py (In-Memory-SQLite über
app.dependency_overrides, StaticPool). Für die "Änderungen übernehmen &
neu formulieren"-Aktion wird `get_attorney_instruction_service` in
app.web.drafts_router direkt gemonkeypatcht, da dieser Aufruf bewusst
NICHT über FastAPIs Depends() läuft (siehe Begründung im Router-Modul-
Docstring: ermöglicht, WritingProviderNotConfiguredError im Routenkörper
selbst abzufangen und eine freundliche Meldung statt eines 500ers zu
zeigen).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.web.drafts_router as drafts_router_module
from app.ai_providers.claude_writing_provider import ClaudeWritingResult
from app.ai_providers.local_ai_provider import RuleBasedLocalAIProvider
from app.attorney_instructions.service import AttorneyInstructionService
from app.db.session import get_db
from app.drafting.service import DraftingService
from app.main import app
from app.models import AttorneyInstruction, Client, Draft, Matter
from app.models.base import Base
from app.privacy.gateway import ClaudePrivacyGateway
from app.privacy.gateway_schema import ClaudeRequestPayload
from app.research.service import LegalResearchService
from app.search.service import DocumentSearchService
from app.web.service_factory import (
    WritingProviderNotConfiguredError,
    get_attorney_instruction_service_for_saving_only,
)
from tests.auth_test_utils import extract_csrf, login_as_admin
from tests.fake_embedding_provider import FakeEmbeddingProvider


class FakeClaudeWritingProvider:
    def __init__(self, response_text: str = "Neu formulierte Antwort.") -> None:
        self.response_text = response_text

    def write(self, payload: ClaudeRequestPayload) -> ClaudeWritingResult:
        return ClaudeWritingResult(text=self.response_text, token_count=10)


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
    # "Anmerkung speichern" braucht keinen echten DraftingService - die
    # Standard-Factory reicht (baut ohnehin drafting_service=None).
    app.dependency_overrides[get_attorney_instruction_service_for_saving_only] = (
        lambda: AttorneyInstructionService(drafting_service=None)
    )
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
    db_session.add_all([client_, matter])
    db_session.commit()
    draft = Draft(matter_id=matter.id, content="Ursprünglicher Entwurfstext.")
    db_session.add(draft)
    db_session.commit()
    return {"matter_id": matter.id, "draft_id": draft.id}


def _working_attorney_instruction_service(db_session: Session) -> AttorneyInstructionService:
    """Baut einen funktionsfähigen Service mit einem Fake-Writing-Provider
    (kein echter Claude-API-Aufruf, kein echter Embedding-Modell-
    Download)."""
    search_service = DocumentSearchService(FakeEmbeddingProvider())
    research_service = LegalResearchService(search_service, min_score_for_sufficient=0.0)
    drafting_service = DraftingService(
        RuleBasedLocalAIProvider(search_service),
        research_service,
        search_service,
        ClaudePrivacyGateway(),
        FakeClaudeWritingProvider(),
        model_name="claude-sonnet-5",
    )
    return AttorneyInstructionService(drafting_service)


# --- GET Entwurfsansicht ---


def test_draft_detail_page_returns_200(client: TestClient, seeded: dict) -> None:
    response = client.get(f"/dashboard/drafts/{seeded['draft_id']}")
    assert response.status_code == 200
    assert "Ursprünglicher Entwurfstext" in response.text
    assert "Anwaltliche Anmerkungen" in response.text


def test_draft_detail_page_shows_version_one_as_only_chip(
    client: TestClient, seeded: dict
) -> None:
    response = client.get(f"/dashboard/drafts/{seeded['draft_id']}")
    assert "v1 · draft" in response.text
    assert "v2 · draft" not in response.text


def test_draft_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/dashboard/drafts/does-not-exist")
    assert response.status_code == 404


def test_draft_detail_page_shows_error_banner_from_query_param(
    client: TestClient, seeded: dict
) -> None:
    response = client.get(
        f"/dashboard/drafts/{seeded['draft_id']}", params={"error": "Testfehler"}
    )
    assert "Testfehler" in response.text
    assert "banner--error" in response.text


def test_draft_detail_page_has_no_error_banner_by_default(
    client: TestClient, seeded: dict
) -> None:
    response = client.get(f"/dashboard/drafts/{seeded['draft_id']}")
    assert "banner--error" not in response.text


# --- Manuelle Bearbeitung ---


def test_manual_edit_creates_new_version_and_redirects(
    client: TestClient, db_session: Session, seeded: dict
) -> None:
    csrf = extract_csrf(client.get(f"/dashboard/drafts/{seeded['draft_id']}").text)
    response = client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/manual-edit",
        data={"content": "Bearbeiteter Text.", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    new_location = response.headers["location"]
    assert new_location != f"/dashboard/drafts/{seeded['draft_id']}"

    new_draft_id = new_location.rsplit("/", 1)[-1]
    new_draft = db_session.get(Draft, new_draft_id)
    assert new_draft.content == "Bearbeiteter Text."
    assert new_draft.version == 2
    assert new_draft.previous_version_id == seeded["draft_id"]

    # Original unveraendert.
    db_session.expire_all()
    original = db_session.get(Draft, seeded["draft_id"])
    assert original.content == "Ursprünglicher Entwurfstext."
    assert original.version == 1


def test_manual_edit_redirect_target_shows_two_version_chips(
    client: TestClient, seeded: dict
) -> None:
    csrf = extract_csrf(client.get(f"/dashboard/drafts/{seeded['draft_id']}").text)
    response = client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/manual-edit",
        data={"content": "Bearbeiteter Text.", "csrf_token": csrf},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "v1" in response.text
    assert "v2" in response.text
    assert "Bearbeiteter Text." in response.text


# --- Anmerkung speichern (ohne Neugenerierung) ---


def test_save_instruction_works_without_configured_api_key(
    client: TestClient, db_session: Session, seeded: dict
) -> None:
    """Kernanforderung/Regressionstest: 'Anmerkung speichern' darf NICHT
    daran scheitern, dass kein Claude-API-Key konfiguriert ist."""
    csrf = extract_csrf(client.get(f"/dashboard/drafts/{seeded['draft_id']}").text)
    response = client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/instructions",
        data={"instruction_text": "Auf Punkt 3 eingehen.", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"/dashboard/drafts/{seeded['draft_id']}"

    instructions = (
        db_session.query(AttorneyInstruction)
        .filter_by(draft_id=seeded["draft_id"])
        .all()
    )
    assert len(instructions) == 1
    assert instructions[0].status == "open"
    assert instructions[0].instruction_text == "Auf Punkt 3 eingehen."


def test_save_instruction_does_not_create_new_draft_version(
    client: TestClient, db_session: Session, seeded: dict
) -> None:
    csrf = extract_csrf(client.get(f"/dashboard/drafts/{seeded['draft_id']}").text)
    client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/instructions",
        data={"instruction_text": "Testanmerkung.", "csrf_token": csrf},
    )
    assert db_session.query(Draft).count() == 1


def test_saved_instruction_appears_on_draft_page(
    client: TestClient, seeded: dict
) -> None:
    csrf = extract_csrf(client.get(f"/dashboard/drafts/{seeded['draft_id']}").text)
    client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/instructions",
        data={"instruction_text": "Ton bestimmter formulieren.", "csrf_token": csrf},
    )
    response = client.get(f"/dashboard/drafts/{seeded['draft_id']}")
    assert "Ton bestimmter formulieren." in response.text
    assert "admin@kanzlei.test" in response.text


# --- Änderungen übernehmen & neu formulieren (mit Fake-Provider) ---


def test_apply_instruction_via_web_creates_new_version(
    client: TestClient, db_session: Session, seeded: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _working_attorney_instruction_service(db_session)
    monkeypatch.setattr(
        drafts_router_module, "get_attorney_instruction_service", lambda: service
    )

    csrf = extract_csrf(client.get(f"/dashboard/drafts/{seeded['draft_id']}").text)
    response = client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/instructions/apply",
        data={
            "instruction_text": "Schadensersatzhöhe nicht anerkennen.",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    new_location = response.headers["location"]
    assert new_location != f"/dashboard/drafts/{seeded['draft_id']}"
    new_draft_id = new_location.rsplit("/", 1)[-1]
    new_draft = db_session.get(Draft, new_draft_id)
    assert new_draft.content == "Neu formulierte Antwort."
    assert new_draft.previous_version_id == seeded["draft_id"]

    instructions = db_session.query(AttorneyInstruction).all()
    assert len(instructions) == 1
    assert instructions[0].status == "applied"
    assert instructions[0].resulting_draft_id == new_draft_id


def test_apply_instruction_without_api_key_shows_friendly_error(
    client: TestClient, seeded: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kein 500er, wenn kein Claude-API-Key konfiguriert ist - stattdessen
    Redirect mit Fehlermeldung im Query-Parameter."""

    def _raise() -> AttorneyInstructionService:
        raise WritingProviderNotConfiguredError("ANTHROPIC_API_KEY ist nicht konfiguriert")

    monkeypatch.setattr(drafts_router_module, "get_attorney_instruction_service", _raise)

    csrf = extract_csrf(client.get(f"/dashboard/drafts/{seeded['draft_id']}").text)
    response = client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/instructions/apply",
        data={"instruction_text": "Testanmerkung.", "csrf_token": csrf},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert seeded["draft_id"] in response.headers["location"]
    assert "error=" in response.headers["location"]


def test_apply_instruction_without_api_key_creates_no_new_draft(
    client: TestClient, db_session: Session, seeded: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise() -> AttorneyInstructionService:
        raise WritingProviderNotConfiguredError("nicht konfiguriert")

    monkeypatch.setattr(drafts_router_module, "get_attorney_instruction_service", _raise)

    csrf = extract_csrf(client.get(f"/dashboard/drafts/{seeded['draft_id']}").text)
    client.post(
        f"/dashboard/drafts/{seeded['draft_id']}/instructions/apply",
        data={"instruction_text": "Testanmerkung.", "csrf_token": csrf},
    )

    assert db_session.query(Draft).count() == 1
    # Auch keine AttorneyInstruction, da der Fehler bereits VOR
    # create_instruction auftritt (Service konnte gar nicht gebaut werden).
    assert db_session.query(AttorneyInstruction).count() == 0
