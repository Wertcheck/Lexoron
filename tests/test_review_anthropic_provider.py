"""Tests fuer app/review/anthropic_review_provider.py (Prompt 18).

Ausschliesslich gegen einen gemockten Anthropic-Client - kein echter
API-Aufruf (kein API-Key in der Sandbox, echter Aufruf in einer Testsuite
unpassend)."""

from unittest.mock import MagicMock, patch

import pytest

from app.privacy.gateway_schema import ClaudeRequestPayload
from app.review.anthropic_review_provider import AnthropicClaudeReviewProvider


def test_requires_non_blank_api_key() -> None:
    with pytest.raises(ValueError):
        AnthropicClaudeReviewProvider(api_key="  ", model="claude-sonnet-5")


@patch("app.review.anthropic_review_provider.anthropic.Anthropic")
def test_review_parses_valid_json_response(mock_anthropic_cls) -> None:
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = (
        '{"findings": [{"category": "formaler_fehler", "severity": "niedrig", '
        '"description": "Anrede fehlt."}], "overall_assessment": "Kleinigkeit."}'
    )
    mock_response = MagicMock()
    mock_response.content = [mock_text_block]
    mock_client.messages.create.return_value = mock_response

    provider = AnthropicClaudeReviewProvider(api_key="test-key", model="claude-sonnet-5")
    payload = ClaudeRequestPayload(
        schreibauftrag="review_draft", anonymisierter_sachverhalt="Text mit [MANDANT_01]."
    )

    result = provider.review(payload)

    assert len(result.findings) == 1
    assert result.findings[0].category == "formaler_fehler"
    assert result.overall_assessment == "Kleinigkeit."


@patch("app.review.anthropic_review_provider.anthropic.Anthropic")
def test_review_raises_on_invalid_json(mock_anthropic_cls) -> None:
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "Das ist kein JSON."
    mock_response = MagicMock()
    mock_response.content = [mock_text_block]
    mock_client.messages.create.return_value = mock_response

    provider = AnthropicClaudeReviewProvider(api_key="test-key", model="claude-sonnet-5")
    payload = ClaudeRequestPayload(
        schreibauftrag="review_draft", anonymisierter_sachverhalt="Text"
    )

    with pytest.raises(ValueError):
        provider.review(payload)


@patch("app.review.anthropic_review_provider.anthropic.Anthropic")
def test_review_uses_review_system_prompt_not_writing_prompt(mock_anthropic_cls) -> None:
    from app.review.provider import REVIEW_SYSTEM_PROMPT

    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = '{"findings": [], "overall_assessment": "OK."}'
    mock_response = MagicMock()
    mock_response.content = [mock_text_block]
    mock_client.messages.create.return_value = mock_response

    provider = AnthropicClaudeReviewProvider(api_key="test-key", model="claude-sonnet-5")
    provider.review(
        ClaudeRequestPayload(schreibauftrag="review_draft", anonymisierter_sachverhalt="Text")
    )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == REVIEW_SYSTEM_PROMPT
