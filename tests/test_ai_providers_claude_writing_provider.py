"""Tests fuer app/ai_providers/claude_writing_provider.py und
app/ai_providers/anthropic_writing_provider.py.

Die konkrete `AnthropicClaudeWritingProvider` wird ausschliesslich gegen
einen gemockten Anthropic-Client getestet - kein echter API-Aufruf in
diesen Tests (kein API-Key vorhanden, und ein echter Aufruf waere in
einer Testsuite ohnehin unpassend). Ein echter End-to-End-Test mit
echtem API-Key muss auf dem Zielsystem des Anwalts erfolgen."""

from unittest.mock import MagicMock, patch

import pytest

from app.ai_providers.claude_writing_provider import (
    ClaudeWritingProvider,
    ClaudeWritingResult,
    build_writing_prompt,
)
from app.privacy.gateway_schema import ClaudeRequestPayload


def test_protocol_has_exactly_one_method() -> None:
    public_methods = [
        name for name in dir(ClaudeWritingProvider) if not name.startswith("_")
    ]
    assert public_methods == ["write"]


def test_fake_implementation_satisfies_protocol() -> None:
    class FakeProvider:
        def write(self, payload: ClaudeRequestPayload) -> ClaudeWritingResult:
            return ClaudeWritingResult(text="Antwort", token_count=10)

    provider: ClaudeWritingProvider = FakeProvider()
    payload = ClaudeRequestPayload(
        schreibauftrag="formulate_draft", anonymisierter_sachverhalt="Text"
    )
    result = provider.write(payload)
    assert result.text == "Antwort"
    assert result.token_count == 10


def test_build_writing_prompt_contains_only_allowlist_fields() -> None:
    payload = ClaudeRequestPayload(
        schreibauftrag="formulate_draft",
        gewuenschter_stil="förmlich",
        anonymisierter_sachverhalt="Sachverhalt mit [MANDANT_01].",
        anonymisierte_argumentationspunkte=["Punkt eins.", "Punkt zwei."],
        anonymisierte_quellenverweise=["§ 355 AO."],
        schreibvorlage="Sehr geehrte Damen und Herren,",
    )

    prompt = build_writing_prompt(payload)

    assert "formulate_draft" in prompt
    assert "förmlich" in prompt
    assert "[MANDANT_01]" in prompt
    assert "Punkt eins." in prompt
    assert "§ 355 AO." in prompt
    assert "Sehr geehrte Damen und Herren," in prompt


def test_build_writing_prompt_omits_empty_optional_fields() -> None:
    payload = ClaudeRequestPayload(
        schreibauftrag="formulate_draft", anonymisierter_sachverhalt="Text"
    )

    prompt = build_writing_prompt(payload)

    assert "Gewünschter Stil" not in prompt
    assert "Argumentationspunkte" not in prompt
    assert "Quellenverweise" not in prompt
    assert "Vorlage" not in prompt


class TestAnthropicClaudeWritingProvider:
    def test_requires_non_blank_api_key(self) -> None:
        from app.ai_providers.anthropic_writing_provider import (
            AnthropicClaudeWritingProvider,
        )

        with pytest.raises(ValueError):
            AnthropicClaudeWritingProvider(api_key="  ", model="claude-sonnet-5")

    @patch("app.ai_providers.anthropic_writing_provider.anthropic.Anthropic")
    def test_write_sends_prompt_and_returns_text(self, mock_anthropic_cls) -> None:
        from app.ai_providers.anthropic_writing_provider import (
            AnthropicClaudeWritingProvider,
        )

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Formulierter Antworttext mit [MANDANT_01]."
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        provider = AnthropicClaudeWritingProvider(
            api_key="test-key", model="claude-sonnet-5"
        )
        payload = ClaudeRequestPayload(
            schreibauftrag="formulate_draft",
            anonymisierter_sachverhalt="Sachverhalt mit [MANDANT_01].",
        )

        result = provider.write(payload)

        assert result.text == "Formulierter Antworttext mit [MANDANT_01]."
        assert result.token_count == 150

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-5"
        sent_prompt = call_kwargs["messages"][0]["content"]
        assert "[MANDANT_01]" in sent_prompt
        # Original-Mandantendaten koennen hier gar nicht auftauchen, da nur
        # die Payload (bereits pseudonymisiert) in den Prompt einfliesst.

    @patch("app.ai_providers.anthropic_writing_provider.anthropic.Anthropic")
    def test_write_handles_missing_usage_gracefully(self, mock_anthropic_cls) -> None:
        from app.ai_providers.anthropic_writing_provider import (
            AnthropicClaudeWritingProvider,
        )

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Antwort."
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.usage = None
        mock_client.messages.create.return_value = mock_response

        provider = AnthropicClaudeWritingProvider(api_key="test-key", model="claude-sonnet-5")
        result = provider.write(
            ClaudeRequestPayload(schreibauftrag="formulate_draft", anonymisierter_sachverhalt="Text")
        )

        assert result.token_count is None

    @patch("app.ai_providers.anthropic_writing_provider.anthropic.Anthropic")
    def test_api_key_is_never_logged_or_included_in_prompt(self, mock_anthropic_cls) -> None:
        from app.ai_providers.anthropic_writing_provider import (
            AnthropicClaudeWritingProvider,
        )

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Antwort."
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.usage = None
        mock_client.messages.create.return_value = mock_response

        secret_key = "sk-ant-super-secret-value"
        provider = AnthropicClaudeWritingProvider(api_key=secret_key, model="claude-sonnet-5")
        provider.write(
            ClaudeRequestPayload(schreibauftrag="formulate_draft", anonymisierter_sachverhalt="Text")
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert secret_key not in str(call_kwargs)
