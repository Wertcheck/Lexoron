"""DraftQualityService – Bewertungen von freigegebenen Entwürfen speichern und auswerten."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import Draft, DraftQualityRating
from app.quality.schema import DraftQualityRatingInput, DraftQualityStats

if TYPE_CHECKING:
    from app.models import User


class DraftQualityService:
    """Verwaltet rückblickende Qualitätsbewertungen von freigegebenen Entwürfen.
    
    Unterschied zu DraftFeedbackService (Prompt 23):
    - DraftFeedback: Bewertung VOR Freigabe (Approval/Rejection/ApprovedWithEdits)
    - DraftQualityRating: Bewertung NACH Freigabe (rückblickend, nur Auswertung)
    
    Ein Anwalt kann MEHRERE Bewertungen zum selben Entwurf abgeben.
    Nur die numerischen Skalen werden aggregiert (zu Statistiken).
    """
    
    def __init__(self, session: Session) -> None:
        self.session = session
    
    def record_rating(
        self,
        draft_id: str,
        rated_by_user_id: str,
        input_data: DraftQualityRatingInput,
    ) -> DraftQualityRating:
        """Neue Bewertung für einen freigegebenen Entwurf speichern.
        
        Args:
            draft_id: ID des zu bewertenden Entwurfs
            rated_by_user_id: ID des Anwalts/Nutzers, der bewertet
            input_data: Bewertungs-Skalen und ggf. Kommentar
        
        Returns:
            Gespeicherte DraftQualityRating
        
        Raises:
            ValueError: wenn input_data keine Inhalte hat (alle Felder leer)
        """
        if not input_data.has_content():
            raise ValueError(
                "Bewertung muss mindestens eine Skala oder einen Kommentar enthalten"
            )
        
        # Prüfe, dass der Entwurf existiert
        draft = self.session.execute(
            select(Draft).where(Draft.id == draft_id)
        ).scalar_one_or_none()
        if not draft:
            raise ValueError(f"Entwurf {draft_id} nicht gefunden")
        
        # Entwurf muss in Status "approved" sein (freigegebene Entwürfe)
        if draft.status != "approved":
            raise ValueError(
                f"Entwurf muss Status 'approved' haben, ist aber '{draft.status}'. "
                "Nur freigegebene Entwürfe können bewertet werden."
            )
        
        # Neue Bewertung anlegen
        rating = DraftQualityRating(
            draft_id=draft_id,
            rated_by_user_id=rated_by_user_id,
            content_quality=input_data.content_quality,
            usefulness=input_data.usefulness,
            completeness=input_data.completeness,
            language_quality=input_data.language_quality,
            comment=input_data.comment if input_data.comment else None,
        )
        
        self.session.add(rating)
        self.session.commit()
        self.session.refresh(rating)
        return rating
    
    def get_ratings_for_draft(self, draft_id: str) -> list[DraftQualityRating]:
        """Alle Bewertungen für einen Entwurf laden (sortiert nach Datum)."""
        return self.session.execute(
            select(DraftQualityRating)
            .where(DraftQualityRating.draft_id == draft_id)
            .order_by(DraftQualityRating.created_at.desc())
        ).scalars().all()
    
    def get_ratings_by_matter(self, matter_id: str) -> list[DraftQualityRating]:
        """Alle Bewertungen für Entwürfe einer Akte laden."""
        return self.session.execute(
            select(DraftQualityRating)
            .join(Draft)
            .where(Draft.matter_id == matter_id)
            .order_by(DraftQualityRating.created_at.desc())
        ).scalars().all()
    
    def compute_stats(self, draft_id: str) -> DraftQualityStats:
        """Aggregierte Statistiken für einen Entwurf berechnen.
        
        Returns:
            DraftQualityStats mit Durchschnitten und Gesamtbewertung
        """
        ratings = self.session.execute(
            select(DraftQualityRating)
            .where(DraftQualityRating.draft_id == draft_id)
        ).scalars().all()
        
        if not ratings:
            return DraftQualityStats(
                draft_id=draft_id,
                total_ratings=0,
                avg_content_quality=None,
                avg_usefulness=None,
                avg_completeness=None,
                avg_language_quality=None,
                avg_overall=None,
            )
        
        # Durchschnitte pro Skala berechnen
        def compute_avg(attr_name: str) -> float | None:
            values = [
                getattr(r, attr_name) for r in ratings
                if getattr(r, attr_name) is not None
            ]
            if values:
                return sum(values) / len(values)
            return None
        
        return DraftQualityStats(
            draft_id=draft_id,
            total_ratings=len(ratings),
            avg_content_quality=compute_avg("content_quality"),
            avg_usefulness=compute_avg("usefulness"),
            avg_completeness=compute_avg("completeness"),
            avg_language_quality=compute_avg("language_quality"),
            avg_overall=None,  # Wird in __post_init__ berechnet
        )
    
    def get_all_ratings_for_period(
        self,
        matter_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[DraftQualityRating]:
        """Alle Bewertungen einer Akte in einem Zeitraum laden (optional).
        
        Args:
            matter_id: ID der Akte
            start_date: Optional: nur Bewertungen ab diesem Datum
            end_date: Optional: nur Bewertungen bis zu diesem Datum
        
        Returns:
            Liste von DraftQualityRating
        """
        query = (
            select(DraftQualityRating)
            .join(Draft)
            .where(Draft.matter_id == matter_id)
        )
        
        if start_date:
            query = query.where(DraftQualityRating.created_at >= start_date)
        if end_date:
            query = query.where(DraftQualityRating.created_at <= end_date)
        
        return self.session.execute(
            query.order_by(DraftQualityRating.created_at.desc())
        ).scalars().all()
