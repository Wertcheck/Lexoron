"""Pydantic-Schemas für Draft Quality Ratings (Prompt 43)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models import DraftQualityRating


class DraftQualityRatingInput(BaseModel):
    """Eingabe: Bewertung eines Entwurfs nach Freigabe.
    
    Alle numerischen Skalen sind optional (der Anwalt kann auch nur einen
    Kommentar abgeben). Die Skalen laufen von 1 (schlecht) bis 5 (exzellent).
    """
    
    content_quality: int | None = None
    usefulness: int | None = None
    completeness: int | None = None
    language_quality: int | None = None
    comment: str | None = None
    
    @field_validator("content_quality", "usefulness", "completeness", "language_quality")
    @classmethod
    def rating_must_be_1_to_5(cls, value: int | None) -> int | None:
        if value is not None and (value < 1 or value > 5):
            raise ValueError("Bewertung muss zwischen 1 und 5 liegen")
        return value
    
    def has_content(self) -> bool:
        """Prüft, ob mindestens eine Bewertung oder ein Kommentar vorhanden ist."""
        return bool(
            self.content_quality is not None
            or self.usefulness is not None
            or self.completeness is not None
            or self.language_quality is not None
            or (self.comment and self.comment.strip())
        )


class DraftQualityRatingOutput(BaseModel):
    """Ausgabe: gespeicherte Bewertung."""
    
    id: str
    draft_id: str
    rated_by_user_id: str
    content_quality: int | None
    usefulness: int | None
    completeness: int | None
    language_quality: int | None
    comment: str | None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


@dataclass
class DraftQualityStats:
    """Aggregierte Statistiken für einen Entwurf."""
    
    draft_id: str
    total_ratings: int
    
    # Durchschnitte (None wenn keine Bewertung für diese Skala abgegeben wurde)
    avg_content_quality: float | None
    avg_usefulness: float | None
    avg_completeness: float | None
    avg_language_quality: float | None
    
    # Übergesamt-Durchschnitt aller bewerteten Skalen
    avg_overall: float | None
    
    def __post_init__(self) -> None:
        """Validierung: avg_overall wird aus den Durchschnitten berechnet."""
        scores = [
            s for s in [
                self.avg_content_quality,
                self.avg_usefulness,
                self.avg_completeness,
                self.avg_language_quality,
            ]
            if s is not None
        ]
        if scores:
            self.avg_overall = sum(scores) / len(scores)
        else:
            self.avg_overall = None
