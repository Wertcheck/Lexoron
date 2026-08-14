"""Schema für Review-Findings und -Ergebnisse."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# Exakt die sieben Kategorien aus dem Konzept (Prompt 18, wörtlich):
# "fehlende Fakten, Widersprüche, unbelegte Rechtsbehauptungen, fehlende
# Quellen, Fristen, Platzhalter und formale Fehler."
ALLOWED_FINDING_CATEGORIES = frozenset(
    {
        "fehlende_fakten",
        "widerspruch",
        "unbelegte_rechtsbehauptung",
        "fehlende_quelle",
        "frist",
        "platzhalter",
        "formaler_fehler",
    }
)
ALLOWED_SEVERITIES = frozenset({"hoch", "mittel", "niedrig"})


class Finding(BaseModel):
    category: str
    severity: str
    description: str

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, value: str) -> str:
        if value not in ALLOWED_FINDING_CATEGORIES:
            raise ValueError(
                f"category muss einer von {sorted(ALLOWED_FINDING_CATEGORIES)} sein"
            )
        return value

    @field_validator("severity")
    @classmethod
    def severity_must_be_known(cls, value: str) -> str:
        if value not in ALLOWED_SEVERITIES:
            raise ValueError(f"severity muss einer von {sorted(ALLOWED_SEVERITIES)} sein")
        return value

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("description darf nicht leer sein")
        return value


class ReviewResult(BaseModel):
    """Rohes Ergebnis vom `ClaudeReviewProvider` - noch pseudonymisiert."""

    findings: list[Finding] = Field(default_factory=list)
    overall_assessment: str


class ReviewOutcome(BaseModel):
    """Endergebnis nach lokaler Rekonstruktion - für die Anwaltsansicht."""

    success: bool
    draft_id: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    overall_assessment: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
