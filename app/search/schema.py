"""Schema für Suchergebnisse.

Jedes Ergebnis verweist auf eine konkrete Entität (`entity_type` +
`entity_id`) - keine generischen/anonymen Treffer, damit "Jede
Suchantwort muss auf konkrete Dokumente verweisen" (Konzept Prompt 11)
technisch erzwungen ist.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

ALLOWED_ENTITY_TYPES = frozenset({"Document", "KnowledgeItem", "Source"})
ALLOWED_MATCH_TYPES = frozenset({"metadata", "fulltext", "semantic", "hybrid"})


class SearchResult(BaseModel):
    entity_type: str
    entity_id: str
    # Nur fuer Document-Treffer gesetzt (KnowledgeItems sind nicht
    # akten-gebunden, siehe Moduldocstring in service.py).
    matter_id: str | None = None
    snippet: str
    score: float = Field(ge=0.0, le=1.0)
    match_type: str

    @field_validator("entity_type")
    @classmethod
    def entity_type_must_be_known(cls, value: str) -> str:
        if value not in ALLOWED_ENTITY_TYPES:
            raise ValueError(
                f"entity_type muss einer von {sorted(ALLOWED_ENTITY_TYPES)} sein"
            )
        return value

    @field_validator("match_type")
    @classmethod
    def match_type_must_be_known(cls, value: str) -> str:
        if value not in ALLOWED_MATCH_TYPES:
            raise ValueError(
                f"match_type muss einer von {sorted(ALLOWED_MATCH_TYPES)} sein"
            )
        return value

    @field_validator("snippet")
    @classmethod
    def snippet_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("snippet darf nicht leer sein")
        return value
