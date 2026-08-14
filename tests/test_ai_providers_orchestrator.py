"""Tests fuer app/ai_providers/orchestrator.py.

Nutzt eine Fake-Implementierung von ClaudeWritingProvider (analog zu
FakeMailProvider/FakeEmbeddingProvider) - kein echter API-Aufruf noetig
und keiner vorhanden."""

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ai_providers.local_ai_provider import RuleBasedLocalAIProvider
from app.ai_providers.orchestrator import DraftGenerationOrchestrator
from app.models import Client, Document, Matter
from app.models.base import Base
from app.privacy.gateway import ClaudePrivacyGateway
from app.privacy.gateway_schema import ClaudeRequestPayload


class FakeClaudeWritingProvider:
    def __init__(self, response_text: str = "Formulierte Antwort.") -> None:
        self.response_text = response_text
        self.received_payloads: list[ClaudeRequestPayload] = []

    def write(self, payload: ClaudeRequestPayload) -> str:
        self.received_payloads.append(payload)
        return self.response_text


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _matter(db: Session, client_name: str = "Max Mustermann", title: str = "Testakte", **kwargs) -> Matter:
    client = Client(name=client_name)
    matter = Matter(client=client, title=title, **kwargs)
    db.add_all([client, matter])
    db.commit()
    return matter


def test_successful_generation_returns_reconstructed_text(db_session: Session) -> None:
    matter = _matter(db_session, client_name="Max Mustermann", title="Testakte")
    document = Document(
        matter=matter,
        file_path="/tmp/x.pdf",
        extracted_text="Mandant Max Mustermann wendet sich gegen den Steuerbescheid.",
    )
    db_session.add(document)
    db_session.commit()

    writing_provider = FakeClaudeWritingProvider(
        response_text="Sehr geehrter Herr [MANDANT_01], wir bestätigen den Eingang."
    )
    orchestrator = DraftGenerationOrchestrator(
        RuleBasedLocalAIProvider(), ClaudePrivacyGateway(), writing_provider
    )

    result = orchestrator.generate_draft_text(matter.id, "formulate_draft", db_session)

    assert result.success is True
    assert result.text == "Sehr geehrter Herr Max Mustermann, wir bestätigen den Eingang."
    assert "[MANDANT_01]" not in result.text


def test_writing_provider_receives_pseudonymized_payload(db_session: Session) -> None:
    matter = _matter(db_session, client_name="Max Mustermann", title="Testakte")
    document = Document(
        matter=matter,
        file_path="/tmp/x.pdf",
        extracted_text="Mandant Max Mustermann bittet um Prüfung.",
    )
    db_session.add(document)
    db_session.commit()
    writing_provider = FakeClaudeWritingProvider()
    orchestrator = DraftGenerationOrchestrator(
        RuleBasedLocalAIProvider(), ClaudePrivacyGateway(), writing_provider
    )

    orchestrator.generate_draft_text(matter.id, "formulate_draft", db_session)

    assert len(writing_provider.received_payloads) == 1
    payload = writing_provider.received_payloads[0]
    assert "Max Mustermann" not in payload.anonymisierter_sachverhalt
    assert "[MANDANT_01]" in payload.anonymisierter_sachverhalt


def test_blocked_request_never_reaches_writing_provider(db_session: Session) -> None:
    matter = _matter(db_session, title="Testakte")
    document = Document(
        matter=matter,
        file_path="/tmp/x.pdf",
        extracted_text="Bitte informieren Sie auch Herrn Peter Müller.",
    )
    db_session.add(document)
    db_session.commit()

    writing_provider = FakeClaudeWritingProvider()
    orchestrator = DraftGenerationOrchestrator(
        RuleBasedLocalAIProvider(), ClaudePrivacyGateway(), writing_provider
    )

    result = orchestrator.generate_draft_text(matter.id, "formulate_draft", db_session)

    assert result.success is False
    assert result.text is None
    assert len(result.blocked_reasons) > 0
    assert writing_provider.received_payloads == []  # NIE aufgerufen


def test_disallowed_purpose_blocks_before_writing_provider(db_session: Session) -> None:
    matter = _matter(db_session, title="Testakte")
    writing_provider = FakeClaudeWritingProvider()
    orchestrator = DraftGenerationOrchestrator(
        RuleBasedLocalAIProvider(), ClaudePrivacyGateway(), writing_provider
    )

    result = orchestrator.generate_draft_text(matter.id, "analyze_full_file", db_session)

    assert result.success is False
    assert writing_provider.received_payloads == []


def test_orchestrator_module_does_not_import_any_claude_sdk() -> None:
    """Architektonischer Schutztest (Vorgabe Punkt 11, wörtlich: 'Der
    Workflow darf nicht direkt von Claude abhängig sein'): das
    Orchestrator-Modul darf kein konkretes SDK/HTTP-Paket importieren."""
    module_path = (
        Path(__file__).resolve().parents[1] / "app" / "ai_providers" / "orchestrator.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))

    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module.split(".")[0])

    forbidden = {"anthropic", "openai", "requests", "httpx", "urllib"}
    assert not (imported_names & forbidden), (
        f"orchestrator.py importiert verbotene Module: {imported_names & forbidden}"
    )
