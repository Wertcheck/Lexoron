"""ReviewFinding – ein einzelner Befund der Review-Engine (Prompt 18).

Isolation über `draft_id` -> `Draft.matter_id` (kein direktes matter_id-
Feld nötig, da jeder Draft bereits strikt einer Akte zugeordnet ist).
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReviewFinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review_findings"

    draft_id: Mapped[str] = mapped_column(
        ForeignKey("drafts.id"), nullable=False, index=True
    )
    # fehlende_fakten / widerspruch / unbelegte_rechtsbehauptung /
    # fehlende_quelle / frist / platzhalter / formaler_fehler
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    # hoch / mittel / niedrig
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
