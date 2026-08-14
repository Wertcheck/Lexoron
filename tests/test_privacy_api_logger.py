"""Tests fuer app/privacy/api_logger.py.

Schwerpunkt: Logs duerfen NIEMALS personenbezogene Inhalte enthalten -
auch nicht ueber Umwege wie Security-Check-Gruende."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import ApiCallLog
from app.models.base import Base
from app.privacy.api_logger import (
    ApiCallLogger,
    categorize_block_reasons,
    compute_anonymized_prompt_id,
)
from app.privacy.gateway_schema import ClaudeRequestPayload


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


def test_categorize_block_reasons_never_contains_original_text() -> None:
    """Kernanforderung: die im Grund enthaltene PII darf NICHT in der
    Kategorie landen."""
    reasons = ["Möglicherweise nicht erkannte Namen/Entitäten gefunden: ['Peter Müller']"]

    category = categorize_block_reasons(reasons)

    assert category == "unrecognized_entity_suspected"
    assert "Peter" not in category
    assert "Müller" not in category


def test_categorize_multiple_reasons_combines_categories() -> None:
    reasons = [
        "Zweck 'analyze_full_file' ist nicht in der Allowlist",
        "Nach Pseudonymisierung weiterhin erkennbare Muster: ['email']",
    ]

    category = categorize_block_reasons(reasons)

    assert "purpose_not_allowed" in category
    assert "residual_pii_detected" in category


def test_categorize_unknown_reason_falls_back_to_generic_category() -> None:
    category = categorize_block_reasons(["Ein völlig neuer, unbekannter Grund."])
    assert category == "unknown_block_reason"


def test_categorize_empty_reasons_returns_none() -> None:
    assert categorize_block_reasons([]) is None


def test_anonymized_prompt_id_is_deterministic_and_short() -> None:
    payload = ClaudeRequestPayload(
        schreibauftrag="formulate_draft", anonymisierter_sachverhalt="Text"
    )

    id_1 = compute_anonymized_prompt_id(payload)
    id_2 = compute_anonymized_prompt_id(payload)

    assert id_1 == id_2
    assert len(id_1) == 16
    # Darf den Inhalt nicht im Klartext enthalten.
    assert "Text" not in id_1


def test_anonymized_prompt_id_differs_for_different_payloads() -> None:
    payload_a = ClaudeRequestPayload(
        schreibauftrag="formulate_draft", anonymisierter_sachverhalt="Text A"
    )
    payload_b = ClaudeRequestPayload(
        schreibauftrag="formulate_draft", anonymisierter_sachverhalt="Text B"
    )

    assert compute_anonymized_prompt_id(payload_a) != compute_anonymized_prompt_id(payload_b)


def test_log_success_persists_safe_fields_only(db_session: Session) -> None:
    logger = ApiCallLogger()
    payload = ClaudeRequestPayload(
        schreibauftrag="formulate_draft",
        anonymisierter_sachverhalt="Mandant [MANDANT_01] bittet um Hilfe.",
    )

    log_entry = logger.log_success(
        db_session,
        workflow_id="matter-123",
        model="claude-sonnet-5",
        purpose="formulate_draft",
        payload=payload,
    )

    assert log_entry.result_status == "success"
    assert log_entry.error_status is None
    assert log_entry.anonymized_prompt_id is not None
    persisted = db_session.query(ApiCallLog).all()
    assert len(persisted) == 1


def test_log_blocked_never_stores_raw_reasons(db_session: Session) -> None:
    logger = ApiCallLogger()

    log_entry = logger.log_blocked(
        db_session,
        workflow_id="matter-123",
        model="claude-sonnet-5",
        purpose="formulate_draft",
        reasons=["Möglicherweise nicht erkannte Namen/Entitäten gefunden: ['Peter Müller']"],
    )

    assert log_entry.result_status == "blocked"
    assert log_entry.error_status == "unrecognized_entity_suspected"
    assert log_entry.anonymized_prompt_id is None
    # Explizit sicherstellen: der Name landet NIRGENDS im DB-Eintrag.
    assert "Peter" not in (log_entry.error_status or "")
    assert "Müller" not in (log_entry.error_status or "")


def test_log_error_never_stores_exception_message(db_session: Session) -> None:
    logger = ApiCallLogger()

    log_entry = logger.log_error(
        db_session, workflow_id="matter-123", model="claude-sonnet-5", purpose="formulate_draft"
    )

    assert log_entry.result_status == "error"
    assert log_entry.error_status == "writing_provider_exception"


def test_api_call_log_model_has_no_free_text_content_field() -> None:
    """Architektonischer Schutztest: das Modell darf kein generisches
    Freitextfeld haben, in dem sich Inhalte verstecken könnten."""
    columns = {c.name for c in ApiCallLog.__table__.columns}
    forbidden_field_names = {"content", "text", "prompt", "response", "details", "message"}
    assert not (columns & forbidden_field_names)
