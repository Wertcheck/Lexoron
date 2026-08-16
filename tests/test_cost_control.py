"""Tests für app/cost_control/ (Prompt 33)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import Settings
from app.cost_control.pricing import estimate_cost_usd
from app.cost_control.service import CostControlService
from app.models import ApiCallLog
from app.models.base import Base


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


# ==========================================================================
# 1. Preisschätzung
# ==========================================================================


def test_estimate_cost_with_exact_split() -> None:
    estimate = estimate_cost_usd(
        "claude-sonnet-5", input_tokens=1_000_000, output_tokens=1_000_000
    )
    assert estimate is not None
    assert estimate.is_exact_split is True
    assert estimate.usd == pytest.approx(18.0)


def test_estimate_cost_falls_back_to_total_tokens() -> None:
    estimate = estimate_cost_usd("claude-sonnet-5", total_tokens=1_000_000)
    assert estimate is not None
    assert estimate.is_exact_split is False
    assert estimate.usd > 0


def test_estimate_cost_prefers_exact_split_over_total() -> None:
    exact = estimate_cost_usd(
        "claude-sonnet-5", input_tokens=800_000, output_tokens=200_000, total_tokens=1_000_000
    )
    assert exact is not None
    assert exact.is_exact_split is True


def test_estimate_cost_returns_none_without_any_token_info() -> None:
    assert estimate_cost_usd("claude-sonnet-5") is None


def test_estimate_cost_unknown_model_falls_back_to_conservative_default() -> None:
    known = estimate_cost_usd(
        "claude-sonnet-5", input_tokens=1_000_000, output_tokens=1_000_000
    )
    unknown = estimate_cost_usd(
        "ein-modell-das-nicht-existiert", input_tokens=1_000_000, output_tokens=1_000_000
    )
    assert known is not None
    assert unknown is not None
    assert unknown.usd >= known.usd


def test_estimate_cost_output_more_expensive_than_input() -> None:
    only_input = estimate_cost_usd("claude-sonnet-5", input_tokens=1000, output_tokens=0)
    only_output = estimate_cost_usd("claude-sonnet-5", input_tokens=0, output_tokens=1000)
    assert only_output.usd > only_input.usd


# ==========================================================================
# 2. CostControlService – Verfolgung
# ==========================================================================


def _add_log(
    db: Session,
    *,
    cost_usd: float,
    status: str = "success",
    created_at: datetime | None = None,
) -> ApiCallLog:
    entry = ApiCallLog(
        workflow_id="matter-123",
        model="claude-sonnet-5",
        purpose="formulate_draft",
        estimated_cost_usd=cost_usd,
        result_status=status,
    )
    if created_at is not None:
        entry.created_at = created_at
    db.add(entry)
    db.commit()
    return entry


def test_current_month_spend_sums_successful_calls(db_session: Session) -> None:
    _add_log(db_session, cost_usd=1.5)
    _add_log(db_session, cost_usd=2.5)
    service = CostControlService()
    assert service.get_current_month_spend_usd(db_session) == pytest.approx(4.0)


def test_current_month_spend_excludes_blocked_and_error_calls(db_session: Session) -> None:
    _add_log(db_session, cost_usd=1.5, status="success")
    _add_log(db_session, cost_usd=99.0, status="blocked")
    _add_log(db_session, cost_usd=99.0, status="error")
    service = CostControlService()
    assert service.get_current_month_spend_usd(db_session) == pytest.approx(1.5)


def test_current_month_spend_excludes_previous_months(db_session: Session) -> None:
    now = datetime.now(timezone.utc)
    last_month = (now.replace(day=1) - timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    _add_log(db_session, cost_usd=50.0, created_at=last_month)
    _add_log(db_session, cost_usd=2.0)
    service = CostControlService()
    assert service.get_current_month_spend_usd(db_session) == pytest.approx(2.0)


def test_total_spend_includes_all_months(db_session: Session) -> None:
    now = datetime.now(timezone.utc)
    last_month = (now.replace(day=1) - timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    _add_log(db_session, cost_usd=50.0, created_at=last_month)
    _add_log(db_session, cost_usd=2.0)
    service = CostControlService()
    assert service.get_total_spend_usd(db_session) == pytest.approx(52.0)


def test_spend_with_no_logs_is_zero(db_session: Session) -> None:
    service = CostControlService()
    assert service.get_current_month_spend_usd(db_session) == 0.0
    assert service.get_total_spend_usd(db_session) == 0.0


# ==========================================================================
# 3. CostControlService – Budget-Kontrolle
# ==========================================================================


def test_no_budget_configured_never_blocks(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_log(db_session, cost_usd=999999.0)
    import app.cost_control.service as module

    monkeypatch.setattr(module, "get_settings", lambda: Settings(monthly_budget_usd=None))
    result = CostControlService().check_before_call(db_session)
    assert result.allowed is True
    assert result.budget_usd is None


def test_budget_not_yet_reached_allows_call(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_log(db_session, cost_usd=10.0)
    import app.cost_control.service as module

    monkeypatch.setattr(
        module, "get_settings", lambda: Settings(monthly_budget_usd=100.0)
    )
    result = CostControlService().check_before_call(db_session)
    assert result.allowed is True
    assert result.current_spend_usd == pytest.approx(10.0)


def test_budget_reached_blocks_call(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_log(db_session, cost_usd=100.0)
    import app.cost_control.service as module

    monkeypatch.setattr(
        module, "get_settings", lambda: Settings(monthly_budget_usd=100.0)
    )
    result = CostControlService().check_before_call(db_session)
    assert result.allowed is False
    assert result.reason is not None
    assert "Kostenlimit" in result.reason


def test_budget_exceeded_blocks_call(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_log(db_session, cost_usd=150.0)
    import app.cost_control.service as module

    monkeypatch.setattr(
        module, "get_settings", lambda: Settings(monthly_budget_usd=100.0)
    )
    result = CostControlService().check_before_call(db_session)
    assert result.allowed is False


def test_warning_threshold_flags_before_hard_block(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_log(db_session, cost_usd=85.0)
    import app.cost_control.service as module

    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: Settings(monthly_budget_usd=100.0, budget_warning_threshold_percent=80),
    )
    result = CostControlService().check_before_call(db_session)
    assert result.allowed is True
    assert result.is_warning is True


def test_below_warning_threshold_no_warning(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_log(db_session, cost_usd=10.0)
    import app.cost_control.service as module

    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: Settings(monthly_budget_usd=100.0, budget_warning_threshold_percent=80),
    )
    result = CostControlService().check_before_call(db_session)
    assert result.allowed is True
    assert result.is_warning is False


# ==========================================================================
# 4. Settings-Validierung
# ==========================================================================


def test_invalid_warning_threshold_rejected() -> None:
    with pytest.raises(Exception):  # noqa: PT011 - pydantic ValidationError
        Settings(budget_warning_threshold_percent=0)
    with pytest.raises(Exception):  # noqa: PT011
        Settings(budget_warning_threshold_percent=150)


def test_valid_warning_threshold_accepted() -> None:
    settings = Settings(budget_warning_threshold_percent=90)
    assert settings.budget_warning_threshold_percent == 90


# ==========================================================================
# 5. Integration: Budget-Blockierung greift tatsächlich VOR dem
#    kostenpflichtigen Aufruf (nicht nur im isolierten Service-Test)
# ==========================================================================


def test_drafting_service_blocks_call_when_budget_exceeded(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Beweis: bei ausgeschöpftem Budget wird der WritingProvider gar
    nicht erst aufgerufen - kein zusätzlicher Kostenanfall."""
    from app.ai_providers.local_ai_provider import RuleBasedLocalAIProvider
    from app.drafting.service import DraftingService
    from app.models import Client, Matter
    from app.privacy.gateway import ClaudePrivacyGateway
    from app.research.service import LegalResearchService
    from app.search.service import DocumentSearchService
    from tests.fake_embedding_provider import FakeEmbeddingProvider

    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte")
    db_session.add_all([client, matter])
    db_session.commit()

    _add_log(db_session, cost_usd=100.0)  # Budget bereits ausgeschoepft

    import app.cost_control.service as cc_module

    monkeypatch.setattr(
        cc_module, "get_settings", lambda: Settings(monthly_budget_usd=100.0)
    )

    class _ProviderThatMustNotBeCalled:
        def write(self, payload):  # noqa: ANN001
            raise AssertionError(
                "WritingProvider wurde trotz ausgeschöpftem Budget aufgerufen!"
            )

    search_service = DocumentSearchService(FakeEmbeddingProvider())
    research_service = LegalResearchService(search_service, min_score_for_sufficient=0.0)
    service = DraftingService(
        RuleBasedLocalAIProvider(search_service),
        research_service,
        search_service,
        ClaudePrivacyGateway(),
        _ProviderThatMustNotBeCalled(),
        model_name="claude-sonnet-5",
    )

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    assert result.success is False
    assert any("Kostenlimit" in reason for reason in result.blocked_reasons)


def test_drafting_service_allows_call_when_budget_not_exceeded(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regressionsschutz: ohne Budget-Überschreitung funktioniert die
    normale Entwurfserstellung unverändert."""
    from app.ai_providers.claude_writing_provider import ClaudeWritingResult
    from app.ai_providers.local_ai_provider import RuleBasedLocalAIProvider
    from app.drafting.service import DraftingService
    from app.models import Client, Matter
    from app.privacy.gateway import ClaudePrivacyGateway
    from app.research.service import LegalResearchService
    from app.search.service import DocumentSearchService
    from tests.fake_embedding_provider import FakeEmbeddingProvider

    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte")
    db_session.add_all([client, matter])
    db_session.commit()

    import app.cost_control.service as cc_module

    monkeypatch.setattr(
        cc_module, "get_settings", lambda: Settings(monthly_budget_usd=100.0)
    )

    class _FakeWritingProvider:
        def write(self, payload):  # noqa: ANN001
            return ClaudeWritingResult(text="Testantwort.", token_count=10)

    search_service = DocumentSearchService(FakeEmbeddingProvider())
    research_service = LegalResearchService(search_service, min_score_for_sufficient=0.0)
    service = DraftingService(
        RuleBasedLocalAIProvider(search_service),
        research_service,
        search_service,
        ClaudePrivacyGateway(),
        _FakeWritingProvider(),
        model_name="claude-sonnet-5",
    )

    result = service.create_draft(matter.id, "formulate_draft", db_session)
    assert result.success is True


def test_api_call_log_stores_estimated_cost_for_successful_draft(
    db_session: Session,
) -> None:
    """Beweis, dass ein erfolgreicher Aufruf tatsächlich einen geschätzten
    Kostenwert speichert - Grundlage der gesamten Kostenkontrolle."""
    from app.ai_providers.claude_writing_provider import ClaudeWritingResult
    from app.ai_providers.local_ai_provider import RuleBasedLocalAIProvider
    from app.drafting.service import DraftingService
    from app.models import Client, Matter
    from app.privacy.gateway import ClaudePrivacyGateway
    from app.research.service import LegalResearchService
    from app.search.service import DocumentSearchService
    from tests.fake_embedding_provider import FakeEmbeddingProvider

    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte")
    db_session.add_all([client, matter])
    db_session.commit()

    class _FakeWritingProvider:
        def write(self, payload):  # noqa: ANN001
            return ClaudeWritingResult(
                text="Testantwort.", input_tokens=1000, output_tokens=200
            )

    search_service = DocumentSearchService(FakeEmbeddingProvider())
    research_service = LegalResearchService(search_service, min_score_for_sufficient=0.0)
    service = DraftingService(
        RuleBasedLocalAIProvider(search_service),
        research_service,
        search_service,
        ClaudePrivacyGateway(),
        _FakeWritingProvider(),
        model_name="claude-sonnet-5",
    )

    service.create_draft(matter.id, "formulate_draft", db_session)

    log_entry = db_session.query(ApiCallLog).filter_by(result_status="success").first()
    assert log_entry is not None
    assert log_entry.input_tokens == 1000
    assert log_entry.output_tokens == 200
    assert log_entry.estimated_cost_usd is not None
    assert log_entry.estimated_cost_usd > 0
