"""Deklarative Basis und Mixins fuer alle Modelle.

Grundsaetze (siehe Konzept §7 / ARCHITECTURE.md §5):
- Eindeutige IDs: UUID4 als String, nicht auto-increment - vermeidet
  erratbare IDs und erleichtert spaeteren Datenaustausch/Export.
- Zeitstempel: `created_at`/`updated_at` auf jeder Entitaet.
- Das Dateisystem enthaelt Originale; die Datenbank fuehrt Beziehungen und
  Status - siehe Document-Modell fuer die konkrete Trennung.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(
        primary_key=True, default=lambda: str(uuid.uuid4())
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
