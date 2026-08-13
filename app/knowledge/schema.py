"""Schema für den Import neuer Kanzleiwissen-Einträge.

Anders als bei Klassifikation/Fristen (KI-generierte Ausgaben) ist das
hier eine Eingabevalidierung für vom Anwalt bereitgestellte Inhalte -
trotzdem strikt geprüft, damit kein leerer/inkonsistenter Eintrag
entsteht.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, field_validator, model_validator


class KnowledgeItemImport(BaseModel):
    title: str
    content: str
    category: str | None = None
    practice_area: str | None = None
    source: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None

    @field_validator("title", "content")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Feld darf nicht leer sein")
        return value

    @model_validator(mode="after")
    def valid_from_must_not_be_after_valid_until(self) -> "KnowledgeItemImport":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from > self.valid_until
        ):
            raise ValueError("valid_from darf nicht nach valid_until liegen")
        return self
