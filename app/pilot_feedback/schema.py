"""Eingabe-Validierung für Pilot-Feedback (Schritt 3) - analog zu
app/feedback/schema.py (Prompt 13)."""

from __future__ import annotations

from pydantic import BaseModel, field_validator

from app.models.pilot_feedback import VALID_FEEDBACK_CATEGORIES


class PilotFeedbackInput(BaseModel):
    category: str
    message: str
    # Bewusst ein einfacher String statt EmailStr - vermeidet eine neue
    # Abhängigkeit (`email-validator`) für ein einzelnes optionales Feld;
    # eine grobe Plausibilitätsprüfung genügt hier (kein Versand an diese
    # Adresse, rein informativ für eine spätere manuelle Rückfrage).
    contact_email: str | None = None

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, value: str) -> str:
        if value not in VALID_FEEDBACK_CATEGORIES:
            raise ValueError(
                f"category muss einer von {sorted(VALID_FEEDBACK_CATEGORIES)} sein, "
                f"war: {value!r}"
            )
        return value

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("message darf nicht leer sein")
        return value

    @field_validator("contact_email")
    @classmethod
    def contact_email_must_look_plausible(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("contact_email sieht nicht wie eine E-Mail-Adresse aus")
        return value
