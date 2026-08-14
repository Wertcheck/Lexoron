"""Schema für Legal-Research-Ergebnisse."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


class LegalResearchFinding(BaseModel):
    """Ein einzelner Treffer MIT vollständigem Quellenbeleg - nie nur ein
    Textschnipsel ohne Herkunft."""

    source_id: str
    title: str
    source_type: str
    reference: str | None = None
    url: str | None = None
    document_date: date | None = None
    snippet: str
    score: float = Field(ge=0.0, le=1.0)
    match_type: str


class LegalResearchResult(BaseModel):
    query: str
    findings: list[LegalResearchFinding] = Field(default_factory=list)
    # Explizit, niemals implizit aus einer leeren Liste abgeleitet -
    # siehe app/research/service.py für die Ermittlung.
    sufficiently_supported: bool
    reasoning: str

    @field_validator("reasoning")
    @classmethod
    def reasoning_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("reasoning darf nicht leer sein")
        return value
