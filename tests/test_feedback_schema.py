"""Tests fuer app/feedback/schema.py (Prompt 13)."""

import pytest
from pydantic import ValidationError

from app.feedback.schema import DraftFeedbackInput


def test_simple_approval_is_valid() -> None:
    feedback = DraftFeedbackInput(approval_status="approved")
    assert feedback.edited_content is None


def test_unknown_status_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DraftFeedbackInput(approval_status="irgendwas")


def test_approved_with_edits_requires_edited_content() -> None:
    with pytest.raises(ValidationError):
        DraftFeedbackInput(approval_status="approved_with_edits")


def test_approved_with_edits_rejects_blank_content() -> None:
    with pytest.raises(ValidationError):
        DraftFeedbackInput(approval_status="approved_with_edits", edited_content="   ")


def test_approved_with_edits_with_content_is_valid() -> None:
    feedback = DraftFeedbackInput(
        approval_status="approved_with_edits", edited_content="Korrigierter Text"
    )
    assert feedback.edited_content == "Korrigierter Text"


def test_rejected_requires_comment() -> None:
    with pytest.raises(ValidationError):
        DraftFeedbackInput(approval_status="rejected")


def test_rejected_with_comment_is_valid() -> None:
    feedback = DraftFeedbackInput(approval_status="rejected", comment="Falsche Rechtsgrundlage")
    assert feedback.comment == "Falsche Rechtsgrundlage"
