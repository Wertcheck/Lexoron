"""User – Benutzer.

Passwort-/Auth-Handling ist bewusst nicht Teil dieses Datenmodells (folgt
mit echter Authentifizierung erst spaeter, kein Vortaeuschen einer
Produktionsauthentifizierung laut Prompt 21)."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_id: Mapped[str | None] = mapped_column(ForeignKey("roles.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role: Mapped["Role | None"] = relationship(back_populates="users")
