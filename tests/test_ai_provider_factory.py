"""Tests für app/ai_providers/factory.py (Prompt 34; Local-First-Umstellung
20.08., siehe ARCHITECTURE.md §60 - AI_MODE ersetzt das frühere
llm_provider-Feld als Provider-Schalter)."""

from __future__ import annotations

import pytest

from app.ai_providers.anthropic_writing_provider import AnthropicClaudeWritingProvider
from app.ai_providers.factory import (
    ProviderNotConfiguredError,
    build_review_provider,
    build_writing_provider,
)
from app.ai_providers.ollama_writing_provider import OllamaWritingProvider
from app.config.settings import Settings
from app.review.anthropic_review_provider import AnthropicClaudeReviewProvider
from app.review.ollama_review_provider import OllamaReviewProvider


def _settings_with_key(**overrides) -> Settings:
    defaults = {"anthropic_api_key": "sk-ant-test-key-00000000000000000000"}
    defaults.update(overrides)
    return Settings(**defaults)


# --- Provider-Auswahl ---


def test_build_writing_provider_returns_ollama_provider_for_default_ai_mode() -> None:
    settings = Settings()
    assert settings.ai_mode == "LOCAL_ONLY"
    provider = build_writing_provider(settings)
    assert isinstance(provider, OllamaWritingProvider)


def test_build_review_provider_returns_ollama_provider_for_default_ai_mode() -> None:
    settings = Settings()
    provider = build_review_provider(settings)
    assert isinstance(provider, OllamaReviewProvider)


def test_build_writing_provider_uses_configured_ollama_base_url_and_model() -> None:
    settings = Settings(ollama_base_url="http://localhost:12345", ollama_model_name="mistral")
    provider = build_writing_provider(settings)
    assert provider.base_url == "http://localhost:12345"
    assert provider.model == "mistral"


def test_build_writing_provider_returns_anthropic_provider_for_hybrid_mode() -> None:
    settings = _settings_with_key(ai_mode="HYBRID")
    provider = build_writing_provider(settings)
    assert isinstance(provider, AnthropicClaudeWritingProvider)


def test_build_review_provider_returns_anthropic_provider_for_hybrid_mode() -> None:
    settings = _settings_with_key(ai_mode="HYBRID")
    provider = build_review_provider(settings)
    assert isinstance(provider, AnthropicClaudeReviewProvider)


def test_build_writing_provider_uses_configured_model_and_max_tokens_in_hybrid_mode() -> None:
    settings = _settings_with_key(
        ai_mode="HYBRID", claude_model_name="claude-opus-4-8", claude_max_tokens=500
    )
    provider = build_writing_provider(settings)
    assert provider.model == "claude-opus-4-8"
    assert provider.max_tokens == 500


# --- Fehlende Zugangsdaten (nur relevant fuer HYBRID/Anthropic) ---


def test_build_writing_provider_raises_when_hybrid_without_api_key() -> None:
    settings = Settings(ai_mode="HYBRID", anthropic_api_key=None)
    with pytest.raises(ProviderNotConfiguredError):
        build_writing_provider(settings)


def test_build_review_provider_raises_when_hybrid_without_api_key() -> None:
    settings = Settings(ai_mode="HYBRID", anthropic_api_key=None)
    with pytest.raises(ProviderNotConfiguredError):
        build_review_provider(settings)


def test_build_writing_provider_raises_when_hybrid_api_key_is_blank() -> None:
    settings = Settings(ai_mode="HYBRID", anthropic_api_key="   ")
    with pytest.raises(ProviderNotConfiguredError):
        build_writing_provider(settings)


def test_build_writing_provider_does_not_require_api_key_in_local_only_mode() -> None:
    """LOCAL_ONLY (Standard) muss ohne jede Anthropic-Konfiguration
    funktionieren - genau der Sinn von "Local-First"."""
    settings = Settings(ai_mode="LOCAL_ONLY", anthropic_api_key=None)
    provider = build_writing_provider(settings)
    assert isinstance(provider, OllamaWritingProvider)


# --- Settings-Validierung (ai_mode) ---


def test_settings_rejects_unsupported_ai_mode() -> None:
    with pytest.raises(Exception):  # noqa: PT011 - pydantic ValidationError
        Settings(ai_mode="CLOUD_ONLY")


def test_settings_accepts_supported_ai_modes() -> None:
    assert Settings(ai_mode="LOCAL_ONLY").ai_mode == "LOCAL_ONLY"
    assert Settings(ai_mode="HYBRID").ai_mode == "HYBRID"


def test_settings_ai_mode_defaults_to_local_only() -> None:
    assert Settings().ai_mode == "LOCAL_ONLY"


# --- Rückwärtskompatibilität (bestehender Code/Tests nutzen den alten Namen) ---


def test_service_factory_reexports_provider_not_configured_error_as_old_name() -> None:
    from app.web.service_factory import WritingProviderNotConfiguredError

    assert WritingProviderNotConfiguredError is ProviderNotConfiguredError
