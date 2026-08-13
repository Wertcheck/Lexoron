"""Tests fuer app/classification/schema.py (Prompt 08)."""

import pytest
from pydantic import ValidationError

from app.classification.schema import ClassificationResult


def test_valid_result_is_accepted() -> None:
    result = ClassificationResult(
        document_type="Rechnung",
        confidence=0.35,
        reasoning="Testbegründung",
    )
    assert result.document_type == "Rechnung"
    assert result.possible_parties == []


def test_unknown_document_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ClassificationResult(
            document_type="Irgendwas Erfundenes",
            confidence=0.5,
            reasoning="Testbegründung",
        )


def test_confidence_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ClassificationResult(
            document_type="Sonstiges", confidence=1.5, reasoning="Testbegründung"
        )
    with pytest.raises(ValidationError):
        ClassificationResult(
            document_type="Sonstiges", confidence=-0.1, reasoning="Testbegründung"
        )


def test_blank_reasoning_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ClassificationResult(document_type="Sonstiges", confidence=0.5, reasoning="   ")


def test_requires_manual_review_respects_threshold() -> None:
    low_confidence = ClassificationResult(
        document_type="Sonstiges", confidence=0.2, reasoning="Testbegründung"
    )
    high_confidence = ClassificationResult(
        document_type="Sonstiges", confidence=0.9, reasoning="Testbegründung"
    )

    assert low_confidence.requires_manual_review(threshold=0.6) is True
    assert high_confidence.requires_manual_review(threshold=0.6) is False
