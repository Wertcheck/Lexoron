"""Schema für Feedback-Eingaben zu einem Entwurf."""

from __future__ import annotations

from pydantic import BaseModel, field_validator, model_validator

ALLOWED_APPROVAL_STATUSES = frozenset({"approved", "approved_with_edits", "rejected"})


class DraftFeedbackInput(BaseModel):
    approval_status: str
    edited_content: str | None = None
    comment: str | None = None

    @field_validator("approval_status")
    @classmethod
    def approval_status_must_be_known(cls, value: str) -> str:
        if value not in ALLOWED_APPROVAL_STATUSES:
            raise ValueError(
                f"approval_status muss einer von {sorted(ALLOWED_APPROVAL_STATUSES)} sein"
            )
        return value

    @model_validator(mode="after")
    def approved_with_edits_requires_edited_content(self) -> "DraftFeedbackInput":
        if self.approval_status == "approved_with_edits" and (
            not self.edited_content or not self.edited_content.strip()
        ):
            raise ValueError(
                "approved_with_edits erfordert einen nicht-leeren edited_content"
            )
        return self

    @model_validator(mode="after")
    def rejection_requires_comment(self) -> "DraftFeedbackInput":
        if self.approval_status == "rejected" and (
            not self.comment or not self.comment.strip()
        ):
            raise ValueError(
                "Ablehnung (rejected) erfordert eine Begründung im Kommentar"
            )
        return self
