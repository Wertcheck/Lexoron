"""User – Benutzer.

Passwort-Handling (Prompt 26): `password_hash` speichert AUSSCHLIESSLICH
einen Argon2-Hash (siehe app/auth/security.py) - an keiner Stelle im
Projekt wird ein Klartext-Passwort persistiert oder geloggt. Nullable,
weil ein Nutzer OHNE Hash sich schlicht nicht anmelden kann (siehe
AuthService.authenticate) - technisch nullable gehalten, um zukünftige
SSO-/Passkey-Nutzer ohne lokales Passwort nicht von vornherein
auszuschließen.
"""

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
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Erzwingt eine Passwortänderung vor dem nächsten Dashboard-Zugriff -
    # insbesondere für den initialen Admin (siehe scripts/create_admin.py)
    # und für von einem Admin neu angelegte Nutzer.
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    role: Mapped["Role | None"] = relationship(back_populates="users")
