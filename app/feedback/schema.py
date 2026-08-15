"""Schema für Feedback-Eingaben zu einem Entwurf."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, field_validator, model_validator

from app.models import Draft, DraftFeedback

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


@dataclass
class DraftFeedbackResult:
    """Rückgabe von `DraftFeedbackService.record_feedback` (Prompt 23).

    `new_draft` ist NUR bei `approval_status == "approved_with_edits"`
    gesetzt - die Bearbeitung erzeugt seit der Versionierungs-Umstellung
    (Prompt 23) eine NEUE `Draft`-Zeile statt die bestehende zu
    überschreiben (siehe app/drafting/versioning.py). `draft` verweist
    unverändert auf die ursprüngliche, unangetastete Version, zu der das
    Feedback abgegeben wurde - `feedback.draft_id` bleibt also weiterhin
    die Version, die der Anwalt tatsächlich bewertet hat, nicht die neue.
    """

    feedback: DraftFeedback
    draft: Draft
    new_draft: Draft | None = None
