"""Source – Rechts-/Wissensquelle (Gesetz, Rechtsprechung, Verordnung ...).

Wichtig (Konzept §6): Rechtsquellen sind eine eigene Schicht, strikt
getrennt von Mandanten-/Aktendaten (keine `matter_id` hier). Jede Quelle
traegt die im Konzept geforderten Metadaten fuer Nachvollziehbarkeit und
Aktualitaet. Die KI darf keine Quelle erfinden - das wird ab Prompt 14/15
technisch durchgesetzt; hier steht nur das Schema.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    # Gesetz / Verordnung / Rechtsprechung / Fachliteratur / interne Leitlinie
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    retrieved_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    # freigegeben / intern / entwurf - endgueltiges Freigabekonzept folgt
    # in Prompt 14.
    approval_level: Mapped[str] = mapped_column(
        String(32), default="entwurf", nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
