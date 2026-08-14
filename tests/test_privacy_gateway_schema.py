"""Tests fuer app/privacy/gateway_schema.py."""

import pytest
from pydantic import ValidationError

from app.privacy.gateway_schema import ClaudeRequestPayload, GatewayResult


def test_valid_payload_is_accepted() -> None:
    payload = ClaudeRequestPayload(
        schreibauftrag="formulate_draft", anonymisierter_sachverhalt="Sachverhalt"
    )
    assert payload.anonymisierte_argumentationspunkte == []


def test_blank_schreibauftrag_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ClaudeRequestPayload(schreibauftrag="  ", anonymisierter_sachverhalt="Text")


def test_blank_sachverhalt_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ClaudeRequestPayload(schreibauftrag="formulate_draft", anonymisierter_sachverhalt="")


def test_gateway_result_defaults() -> None:
    result = GatewayResult(allowed=False, purpose="formulate_draft")
    assert result.payload is None
    assert result.mappings == []
    assert result.reasons == []
