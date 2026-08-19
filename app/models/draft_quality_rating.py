"""DraftQualityRating – Rückblickende Qualitätsbewertung nach Freigabe.

Unterschied zu DraftFeedback (Prompt 23):
- DraftFeedback = Bewertung/Überprüfung VOR Freigabe (Approval/Rejection/ApprovedWithEdits)
- DraftQualityRating = Bewertung NACH Freigabe (rückblickend, wie nützlich/korrekt war der
  freigegebene Entwurf? nur Auswertung, kein Auto-Training)

Ein Anwalt kann MEHRERE Bewertungen zu derselben Draft abgeben (z. B. sofort nach
Freigabe, und dann nochmal eine Woche später, nachdem der Entwurf in der Praxis
getestet wurde). Nur die (optionalen) quantitativen Skalen werden aggregiert.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DraftQualityRating(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "draft_quality_ratings"

    draft_id: Mapped[str] = mapped_column(
        ForeignKey("drafts.id"), nullable=False, index=True
    )
    rated_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    # Skalen 1-5 (optional):
    # - content_quality: "War der Inhalt rechtlich korrekt/präzise?"
    # - usefulness: "War der Entwurf praktisch verwendbar?"
    # - completeness: "War die Akte/der Kontext hinreichend erfasst?"
    # - language_quality: "War die Sprache/Formulierung angemessen?"
    # Nullable = der Anwalt kann auch NUR einen Kommentar abgeben ohne Zahlen.
    content_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usefulness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completeness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Freetext-Anmerkungen (optional)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    draft: Mapped["Draft"] = relationship(back_populates="quality_ratings")
    rated_by_user: Mapped["User"] = relationship()
