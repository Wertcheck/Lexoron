"""Tests fuer app/deadlines/schema.py (Prompt 10)."""

import pytest
from pydantic import ValidationError

from app.deadlines.schema import ExtractedDeadline


def test_valid_deadline_is_accepted() -> None:
    result = ExtractedDeadline(
        source_text="...bis zum 15.03.2027...",
        raw_date_text="15.03.2027",
        confidence=0.5,
        reasoning="Testbegründung",
    )
    assert result.due_date is None


def test_confidence_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ExtractedDeadline(
            source_text="Text",
            raw_date_text="15.03.2027",
            confidence=1.5,
            reasoning="Testbegründung",
        )


def test_blank_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ExtractedDeadline(
            source_text="   ",
            raw_date_text="15.03.2027",
            confidence=0.5,
            reasoning="Testbegründung",
        )
    with pytest.raises(ValidationError):
        ExtractedDeadline(
            source_text="Text",
            raw_date_text="15.03.2027",
            confidence=0.5,
            reasoning="   ",
        )
