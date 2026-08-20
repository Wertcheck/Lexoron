"""Tests für die lokalen Ollama-Provider (Local-First-Umstellung 20.08.,
siehe ARCHITECTURE.md §60): app/ai_providers/ollama_writing_provider.py und
app/review/ollama_review_provider.py. Kein echter Netzwerkaufruf - `httpx`
wird auf Modulebene gemockt, analog zu den Anthropic-Provider-Tests in
tests/test_no_ai_gateway_proxy.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.ai_providers.ollama_writing_provider import (
    OllamaUnavailableError,
    OllamaWritingProvider,
)
from app.privacy.gateway_schema import ClaudeRequestPayload
from app.review.ollama_review_provider import OllamaReviewProvider


def _payload(**overrides) -> ClaudeRequestPayload:
    defaults = {"schreibauftrag": "formulate_draft", "anonymisierter_sachverhalt": "Text"}
    defaults.update(overrides)
    return ClaudeRequestPayload(**defaults)


# --- Konstruktion ---


def test_writing_provider_rejects_blank_base_url() -> None:
    with pytest.raises(ValueError):
        OllamaWritingProvider(base_url="", model="llama3.1")


def test_writing_provider_rejects_blank_model() -> None:
    with pytest.raises(ValueError):
        OllamaWritingProvider(base_url="http://localhost:11434", model="")


def test_review_provider_rejects_blank_base_url() -> None:
    with pytest.raises(ValueError):
        OllamaReviewProvider(base_url="", model="llama3.1")


# --- Erfolgreicher Aufruf ---


def test_write_sends_chat_request_and_parses_result() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "message": {"content": "Sehr geehrte Damen und Herren, ..."},
        "prompt_eval_count": 120,
        "eval_count": 40,
    }

    with patch(
        "app.ai_providers.ollama_writing_provider.httpx.post", return_value=mock_response
    ) as mock_post:
        provider = OllamaWritingProvider(base_url="http://localhost:11434/", model="llama3.1")
        result = provider.write(_payload())

    assert result.text == "Sehr geehrte Damen und Herren, ..."
    assert result.input_tokens == 120
    assert result.output_tokens == 40
    assert result.token_count == 160

    call_url = mock_post.call_args.args[0]
    call_kwargs = mock_post.call_args.kwargs
    # base_url-Trailing-Slash wird sauber entfernt, kein "//api/chat".
    assert call_url == "http://localhost:11434/api/chat"
    assert call_kwargs["json"]["model"] == "llama3.1"
    assert call_kwargs["json"]["stream"] is False


def test_review_sends_chat_request_with_json_format_and_parses_result() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "message": {
            "content": '{"findings": [], "overall_assessment": "In Ordnung."}'
        },
        "prompt_eval_count": 200,
        "eval_count": 30,
    }

    with patch(
        "app.review.ollama_review_provider.httpx.post", return_value=mock_response
    ) as mock_post:
        provider = OllamaReviewProvider(base_url="http://localhost:11434", model="llama3.1")
        result = provider.review(_payload())

    assert result.findings == []
    assert result.overall_assessment == "In Ordnung."
    assert mock_post.call_args.kwargs["json"]["format"] == "json"


def test_review_raises_value_error_on_invalid_json() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"message": {"content": "kein json"}}

    with patch("app.review.ollama_review_provider.httpx.post", return_value=mock_response):
        provider = OllamaReviewProvider(base_url="http://localhost:11434", model="llama3.1")
        with pytest.raises(ValueError):
            provider.review(_payload())


# --- Nicht erreichbar ---


def test_write_raises_ollama_unavailable_error_when_connection_fails() -> None:
    with patch(
        "app.ai_providers.ollama_writing_provider.httpx.post",
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        provider = OllamaWritingProvider(base_url="http://localhost:11434", model="llama3.1")
        with pytest.raises(OllamaUnavailableError):
            provider.write(_payload())


def test_review_raises_ollama_unavailable_error_when_connection_fails() -> None:
    with patch(
        "app.review.ollama_review_provider.httpx.post",
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        provider = OllamaReviewProvider(base_url="http://localhost:11434", model="llama3.1")
        with pytest.raises(OllamaUnavailableError):
            provider.review(_payload())


# --- Struktureller Datenschutz (analog zu tests/test_no_ai_gateway_proxy.py) ---


def test_write_call_never_leaks_matter_document_or_message_models() -> None:
    """Wie bei den Anthropic-Providern: die Payload-Klasse besitzt strukturell
    keine Felder für rohe Aktendaten - dieser Test beweist es auf
    Typebene, nicht nur per Konvention."""
    field_names = set(ClaudeRequestPayload.model_fields.keys())
    forbidden = {"matter_id", "document", "message", "matter", "attachments"}
    assert not (field_names & forbidden)
