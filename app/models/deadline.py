"""Deadline – (moegliche) Frist.

Wichtig (Konzept Prompt 10): Eine erkannte Frist darf nie automatisch als
endgueltig verbindlich gelten. Jede Deadline traegt daher Quelle
(`document_id`, `source_text`), eine Konfidenz und einen expliziten
Pruefstatus. Die eigentliche Erkennungslogik entsteht erst in Prompt 10 -
hier wird nur das Schema vorgesehen.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Deadline(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deadlines"

    matter_id: Mapped[str] = mapped_column(
        ForeignKey("matters.id"), nullable=False, index=True
    )
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # unreviewed / confirmed / rejected - niemals automatisch "confirmed".
    review_status: Mapped[str] = mapped_column(
        String(32), default="unreviewed", nullable=False
    )

    matter: Mapped["Matter"] = relationship(back_populates="deadlines")
