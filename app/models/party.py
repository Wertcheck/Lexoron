"""Party – Beteiligter einer Akte (z. B. Gegenseite, Zeuge, gegnerischer
Anwalt). Bewusst generisch gehalten; feinere Rollen-/Typisierung kann
spaeter ergaenzt werden, ohne das Schema grundlegend zu aendern."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Party(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "parties"

    matter_id: Mapped[str] = mapped_column(
        ForeignKey("matters.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    matter: Mapped["Matter"] = relationship(back_populates="parties")
