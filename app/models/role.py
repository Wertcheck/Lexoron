"""Role – Benutzerrolle.

Seit Prompt 26: drei Rollen (Admin, Anwalt, Mitarbeiter) werden als
SEED-DATEN angelegt (Alembic-Datenmigration, siehe migrations/versions/
..._seed_default_roles.py), NICHT als fest im Code verdrahtete Konstanten
- damit später weitere kanzleispezifische Rollen möglich bleiben, ohne
das Datenmodell zu ändern (passt zum Multi-Kanzlei-Ziel).

Die eigentliche RECHTE-MATRIX (welche Rolle darf was) ist bewusst NICHT
Teil dieses Modells, sondern lebt in app/auth/permissions.py, verknüpft
über den Rollennamen (`Role.name`). Grund: die drei Rollen und ihre
exakten Berechtigungen wurden vom Anwalt als feste fachliche Vorgabe
definiert (keine admin-editierbare Rechteverwaltung in diesem Prompt) -
eine vollständige Role-Permission-Datenbanktabelle wäre an dieser Stelle
vorzeitige Komplexität ohne aktuellen Bedarf. Siehe ARCHITECTURE.md §38
für die Abwägung und einen möglichen späteren Ausbauschritt.
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
