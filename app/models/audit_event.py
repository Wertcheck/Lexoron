"""AuditEvent – unveraenderliches Ereignis.

Wichtig (Konzept Prompt 19 / CLAUDE.md): Audit-Events sind append-only -
im Gegensatz zu allen anderen Modellen daher bewusst OHNE `updated_at`
(kein TimestampMixin, nur `created_at`). Anwendungscode darf Audit-Events
nur erzeugen, nie aendern oder loeschen (wird technisch/organisatorisch
erst in Prompt 19 vollstaendig durchgesetzt).

`entity_type`/`entity_id` referenzieren generisch die betroffene Entitaet
(z. B. "Matter"/"<id>"), damit ein Audit-Event zu jeder Art von Objekt
erzeugt werden kann, ohne fuer jede Entitaet eine eigene Audit-Tabelle zu
brauchen. `details` darf laut Grundregel keine unnoetigen sensiblen
Mandanteninhalte enthalten - nur Verweise/knappe Beschreibungen.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # z. B. "system", "ai", oder eine User-ID.
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
