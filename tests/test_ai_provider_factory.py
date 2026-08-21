"""Tests für app/ai_providers/factory.py (Prompt 34; seit §63 ausschließlich
Anthropic/Claude, siehe ARCHITECTURE.md §63 - Ollama vollständig entfernt,
kein `ai_mode`-Schalter mehr)."""

from __future__ import annotations

import pytest

from app.ai_providers.anthropic_writing_provider import AnthropicClaudeWritingProvider
from app.ai_providers.factory import (
    ProviderNotConfiguredError,
    build_local_llm_provider,
    build_review_provider,
    build_writing_provider,
)
from app.ai_providers.ollama_provider import OllamaLocalLLMProvider
from app.config.settings import Settings
from app.review.anthropic_review_provider import AnthropicClaudeReviewProvider


def _settings_with_key(**overrides) -> Settings:
    defaults = {"anthropic_api_key": "sk-ant-test-key-00000000000000000000"}
    defaults.update(overrides)
    return Settings(**defaults)


# --- Provider-Auswahl ---


def test_build_writing_provider_returns_anthropic_provider() -> None:
    settings = _settings_with_key()
    provider = build_writing_provider(settings)
    assert isinstance(provider, AnthropicClaudeWritingProvider)


def test_build_review_provider_returns_anthropic_provider() -> None:
    settings = _settings_with_key()
    provider = build_review_provider(settings)
    assert isinstance(provider, AnthropicClaudeReviewProvider)


def test_build_writing_provider_uses_configured_model_and_max_tokens() -> None:
    settings = _settings_with_key(claude_model_name="claude-opus-4-8", claude_max_tokens=500)
    provider = build_writing_provider(settings)
    assert provider.model == "claude-opus-4-8"
    assert provider.max_tokens == 500


# --- Fehlende Zugangsdaten ---


def test_build_writing_provider_raises_without_api_key() -> None:
    settings = Settings(anthropic_api_key=None)
    with pytest.raises(ProviderNotConfiguredError):
        build_writing_provider(settings)


def test_build_review_provider_raises_without_api_key() -> None:
    settings = Settings(anthropic_api_key=None)
    with pytest.raises(ProviderNotConfiguredError):
        build_review_provider(settings)


def test_build_writing_provider_raises_when_api_key_is_blank() -> None:
    settings = Settings(anthropic_api_key="   ")
    with pytest.raises(ProviderNotConfiguredError):
        build_writing_provider(settings)


# --- Lokale KI (§65) ---


def test_build_local_llm_provider_returns_none_when_disabled() -> None:
    settings = Settings(local_ai_enabled=False)
    assert build_local_llm_provider(settings) is None


def test_build_local_llm_provider_returns_ollama_provider_when_enabled() -> None:
    settings = Settings(
        local_ai_enabled=True, ollama_base_url="http://localhost:12345", ollama_model="qwen3:8b"
    )
    provider = build_local_llm_provider(settings)
    assert isinstance(provider, OllamaLocalLLMProvider)
    assert provider.base_url == "http://localhost:12345"
    assert provider.model == "qwen3:8b"


def test_settings_rejects_unsupported_local_ai_runtime() -> None:
    with pytest.raises(Exception):  # noqa: PT011 - pydantic ValidationError
        Settings(local_ai_runtime="lmstudio")


def test_settings_local_ai_disabled_by_default() -> None:
    assert Settings().local_ai_enabled is False


# --- Rückwärtskompatibilität (bestehender Code/Tests nutzen den alten Namen) ---


def test_service_factory_reexports_provider_not_configured_error_as_old_name() -> None:
    from app.web.service_factory import WritingProviderNotConfiguredError

    assert WritingProviderNotConfiguredError is ProviderNotConfiguredError
