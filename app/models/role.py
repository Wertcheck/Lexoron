"""Role – Benutzerrolle.

Konkrete Rollen (Administrator, Anwalt, Mitarbeiter) und Rechte-Logik
entstehen erst in Prompt 26. Hier nur das minimale Schema, damit `User`
bereits referenzieren kann.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="role")
