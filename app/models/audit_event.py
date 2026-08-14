"""AuditEvent – unveraenderliches Ereignis.

Wichtig (Konzept Prompt 19 / CLAUDE.md): Audit-Events sind append-only -
im Gegensatz zu allen anderen Modellen daher bewusst OHNE `updated_at`
(kein TimestampMixin, nur `created_at`). Anwendungscode darf Audit-Events
nur erzeugen, nie aendern oder loeschen.

Ab Prompt 19 ist das append-only-Prinzip nicht mehr nur Konvention,
sondern technisch erzwungen: `_prevent_update`/`_prevent_delete` (SQLAlchemy-
Mapper-Events) werfen `AuditLogImmutableError`, sobald ein bereits
gespeichertes `AuditEvent` ueber die ORM-Session veraendert oder geloescht
werden soll (siehe Ende dieser Datei). Das faengt versehentliche
Aenderungsversuche im Anwendungscode ab - kein Schutz gegen rohes SQL
ausserhalb der ORM-Session, das ist eine bewusste, dokumentierte Grenze.

`entity_type`/`entity_id` referenzieren generisch die betroffene Entitaet
(z. B. "Matter"/"<id>"), damit ein Audit-Event zu jeder Art von Objekt
erzeugt werden kann, ohne fuer jede Entitaet eine eigene Audit-Tabelle zu
brauchen. `details` darf laut Grundregel keine unnoetigen sensiblen
Mandanteninhalte enthalten - nur Verweise/knappe Beschreibungen. Als
technischer Rueckhalt dazu (nicht nur Disziplin): `details` wird bei
Ueberschreitung von `MAX_DETAILS_LENGTH` automatisch gekuerzt (siehe
`_truncate_details`) - verhindert, dass versehentlich ein grosser
Textblob (z. B. ein ganzer Dokumentinhalt) im Log landet.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.models.base import Base, UUIDPrimaryKeyMixin


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLogImmutableError(Exception):
    """Wird ausgeloest, wenn versucht wird, ein bestehendes AuditEvent zu
    aendern oder zu loeschen - Audit-Events sind append-only."""


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"

    MAX_DETAILS_LENGTH = 1000
    _TRUNCATION_SUFFIX = " […gekürzt]"

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # z. B. "system", "ai", oder eine User-ID.
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    @validates("details")
    def _truncate_details(self, key: str, value: str | None) -> str | None:
        if value is None or len(value) <= self.MAX_DETAILS_LENGTH:
            return value
        cutoff = self.MAX_DETAILS_LENGTH - len(self._TRUNCATION_SUFFIX)
        return value[:cutoff] + self._TRUNCATION_SUFFIX


@event.listens_for(AuditEvent, "before_update")
def _prevent_update(mapper, connection, target: AuditEvent) -> None:  # noqa: ANN001
    raise AuditLogImmutableError(
        "AuditEvent ist append-only und darf nicht geändert werden."
    )


@event.listens_for(AuditEvent, "before_delete")
def _prevent_delete(mapper, connection, target: AuditEvent) -> None:  # noqa: ANN001
    raise AuditLogImmutableError(
        "AuditEvent ist append-only und darf nicht gelöscht werden."
    )
