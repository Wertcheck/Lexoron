"""Tests fuer app/review/schema.py (Prompt 18)."""

import pytest
from pydantic import ValidationError

from app.review.schema import Finding, ReviewOutcome, ReviewResult


def test_valid_finding_is_accepted() -> None:
    finding = Finding(category="formaler_fehler", severity="niedrig", description="Text")
    assert finding.severity == "niedrig"


def test_unknown_category_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Finding(category="irgendwas", severity="niedrig", description="Text")


def test_unknown_severity_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Finding(category="formaler_fehler", severity="kritisch", description="Text")


def test_blank_description_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Finding(category="formaler_fehler", severity="niedrig", description="   ")


def test_review_result_defaults_to_empty_findings() -> None:
    result = ReviewResult(overall_assessment="In Ordnung.")
    assert result.findings == []


def test_review_outcome_defaults() -> None:
    outcome = ReviewOutcome(success=False)
    assert outcome.findings == []
    assert outcome.blocked_reasons == []
