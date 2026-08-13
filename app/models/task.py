"""Task – Aufgabe innerhalb einer Akte."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    matter_id: Mapped[str] = mapped_column(
        ForeignKey("matters.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # open / done - bewusst einfach gehalten; Prioritaeten/Eskalation folgen
    # bei Bedarf in spaeteren Prompts (Dashboard, Fristen-Service).
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)

    matter: Mapped["Matter"] = relationship(back_populates="tasks")
