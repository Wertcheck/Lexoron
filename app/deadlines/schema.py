"""Schema für extrahierte Fristkandidaten."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


class ExtractedDeadline(BaseModel):
    # Kurzer Kontextausschnitt aus dem Originaltext (NICHT der ganze
    # Dokumenttext) - das ist die "Textstelle" aus der Konzeptvorgabe.
    source_text: str
    # Die im Text roh gefundene Datums-/Fristangabe, z. B. "15.03.2027"
    # oder "binnen zwei Wochen" - bleibt auch erhalten, wenn kein
    # konkretes Datum auflösbar war.
    raw_date_text: str
    # Nur gesetzt, wenn ein konkretes Kalenderdatum ermittelt werden
    # konnte (z. B. bei "binnen zwei Wochen" ohne Bezugsdatum: None).
    due_date: date | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

    @field_validator("source_text", "raw_date_text", "reasoning")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Feld darf nicht leer sein")
        return value
