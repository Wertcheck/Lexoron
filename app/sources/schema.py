"""Schema für den Import einer Rechtsquelle."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, field_validator, model_validator

ALLOWED_SOURCE_TYPES = frozenset(
    {
        "Gesetz",
        "Verordnung",
        # Bewusst als eigener Typ (nicht unter "Sonstiges"): BMF-Schreiben
        # und vergleichbare Verwaltungsanweisungen sind in der
        # steuerrechtlichen Praxis von zentraler Bedeutung.
        "Verwaltungsanweisung",
        "Rechtsprechung",
        "Fachliteratur",
        "Interne Leitlinie",
        "Sonstiges",
    }
)


class SourceImport(BaseModel):
    title: str
    source_type: str
    reference: str | None = None
    url: str | None = None
    document_date: date | None = None
    retrieved_at: date | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("title darf nicht leer sein")
        return value

    @field_validator("source_type")
    @classmethod
    def source_type_must_be_known(cls, value: str) -> str:
        if value not in ALLOWED_SOURCE_TYPES:
            raise ValueError(
                f"source_type muss einer von {sorted(ALLOWED_SOURCE_TYPES)} sein"
            )
        return value

    @model_validator(mode="after")
    def valid_from_must_not_be_after_valid_until(self) -> "SourceImport":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from > self.valid_until
        ):
            raise ValueError("valid_from darf nicht nach valid_until liegen")
        return self
