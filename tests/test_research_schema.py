"""Tests fuer app/research/schema.py (Prompt 15)."""

import pytest
from pydantic import ValidationError

from app.research.schema import LegalResearchResult


def test_valid_result_is_accepted() -> None:
    result = LegalResearchResult(
        query="Testfrage",
        findings=[],
        sufficiently_supported=False,
        reasoning="Nicht ausreichend belegt: keine Quelle gefunden.",
    )
    assert result.findings == []


def test_blank_reasoning_is_rejected() -> None:
    with pytest.raises(ValidationError):
        LegalResearchResult(
            query="Testfrage", sufficiently_supported=False, reasoning="   "
        )
