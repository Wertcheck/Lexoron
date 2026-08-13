"""Client – Mandant.

Oberste Isolationsebene: jede Matter (Akte) gehoert zu genau einem Client.
Kontext-/Wissensabruf darf nie ueber die Grenze eines Client hinweg
vermischen (siehe ARCHITECTURE.md §7, wird vollstaendig erst in Prompt 11
und 41 technisch durchgesetzt).
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Client(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_number: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    matters: Mapped[list["Matter"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
