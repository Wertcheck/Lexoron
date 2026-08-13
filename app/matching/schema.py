"""Schema für Aktenzuordnungs-Ergebnisse."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

ALLOWED_MATCH_DECISIONS = frozenset({"auto_assigned", "needs_review", "no_match"})


class MatchCandidate(BaseModel):
    """Eine mögliche Akte mit Score und den Signalen, die dafür sprachen."""

    matter_id: str
    score: float = Field(ge=0.0, le=1.0)
    matched_signals: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    decision: str
    # Nur bei decision == "auto_assigned" gesetzt - siehe matcher.py.
    matter_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    # Alle gefundenen Kandidaten (auch bei needs_review/no_match), damit ein
    # späteres Dashboard (Prompt 22) Vorschläge anzeigen kann, ohne dass hier
    # bereits eine Zuordnung stattfindet.
    candidates: list[MatchCandidate] = Field(default_factory=list)

    @field_validator("decision")
    @classmethod
    def decision_must_be_known(cls, value: str) -> str:
        if value not in ALLOWED_MATCH_DECISIONS:
            raise ValueError(
                f"decision muss einer von {sorted(ALLOWED_MATCH_DECISIONS)} sein, "
                f"nicht {value!r}"
            )
        return value

    @field_validator("reasoning")
    @classmethod
    def reasoning_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("reasoning darf nicht leer sein")
        return value
