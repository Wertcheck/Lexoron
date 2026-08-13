"""Tests fuer app/matching/schema.py (Prompt 09)."""

import pytest
from pydantic import ValidationError

from app.matching.schema import MatchResult


def test_valid_result_is_accepted() -> None:
    result = MatchResult(decision="no_match", confidence=0.0, reasoning="Testgrund")
    assert result.decision == "no_match"
    assert result.matter_id is None


def test_unknown_decision_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MatchResult(decision="irgendwas", confidence=0.5, reasoning="Testgrund")


def test_blank_reasoning_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MatchResult(decision="no_match", confidence=0.0, reasoning="   ")


def test_confidence_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MatchResult(decision="no_match", confidence=1.1, reasoning="Testgrund")
