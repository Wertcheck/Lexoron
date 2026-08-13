"""Draft – Antwortentwurf.

Versionierung ist hier zentral: jede Ueberarbeitung erhoeht `version`, statt
den vorherigen Stand zu ueberschreiben (Nachvollziehbarkeit, siehe
Konzept §5 Feedback-Learning und Prompt 24 Versionsvergleich). `status`
bildet den Freigabeweg ab, ersetzt aber nicht die vollstaendige
Workflow-State-Machine aus Prompt 20/ARCHITECTURE.md §6.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Draft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drafts"

    matter_id: Mapped[str] = mapped_column(
        ForeignKey("matters.id"), nullable=False, index=True
    )
    message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # draft / legal_review / approved / rejected - siehe Hinweis oben.
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    matter: Mapped["Matter"] = relationship(back_populates="drafts")
