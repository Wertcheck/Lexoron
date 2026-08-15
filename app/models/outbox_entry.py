"""OutboxEntry – Postausgang-Eintrag für einen freigegebenen Entwurf
(Prompt 25).

GRUNDREGEL (CLAUDE.md, wörtlich): "Keine automatische externe
Kommunikation (insb. E-Mail-Versand) ohne explizite Freigabe." Dieselbe
architektonische Entscheidung wie beim `MailProvider` (app/mail/base.py:
strukturell KEINE Sende-Methode, "auf Code-Ebene unmöglich, nicht nur per
Einstellung deaktiviert") gilt hier genauso: Dieses Modell und der
zugehörige `OutboxService` (app/outbox/service.py) haben KEINEN Codepfad,
der eine E-Mail tatsächlich verschickt (kein SMTP, kein Aufruf einer
Versand-API). Der Postausgang ist eine WARTESCHLANGE mit manueller
Sende-BESTÄTIGUNG - der tatsächliche Versand geschieht außerhalb dieses
Systems (z. B. über das eigene E-Mail-Programm des Anwalts), das System
hält nur fest, DASS und WANN der Anwalt bestätigt hat, versendet zu haben.

`status`:
- "pending": freigegeben, wartet auf Versand (durch den Anwalt, außerhalb
  des Systems) und anschließende Bestätigung.
- "sent": der Anwalt hat manuell bestätigt, das Schreiben versendet zu
  haben (`sent_at`/`sent_by` gesetzt).

Ein `Draft` bekommt bei Freigabe GENAU EINEN `OutboxEntry` (siehe
`OutboxService.add_to_outbox` - `draft_id` ist UNIQUE).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

VALID_OUTBOX_STATUSES = ("pending", "sent")


class OutboxEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outbox_entries"

    # Redundant zu draft.matter_id, aber bewusst direkt gehalten - gleiches
    # Muster wie AttorneyInstruction.matter_id (Prompt 23): ermöglicht
    # Aktenisolations-Abfragen ohne Join.
    matter_id: Mapped[str] = mapped_column(
        ForeignKey("matters.id"), nullable=False, index=True
    )
    draft_id: Mapped[str] = mapped_column(
        ForeignKey("drafts.id"), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Freitext wie AuditEvent.actor/DraftFeedback.actor - bewusst keine
    # strikte FK auf User (konsistent mit dem übrigen Projekt).
    sent_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    draft: Mapped["Draft"] = relationship()
