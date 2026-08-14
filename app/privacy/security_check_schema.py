"""Schema für das Ergebnis des Security-Checks."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SecurityCheckResult(BaseModel):
    passed: bool
    # Menschlich lesbare Gründe - bei passed=False IMMER mindestens einer.
    # Leer bei passed=True.
    reasons: list[str] = Field(default_factory=list)
