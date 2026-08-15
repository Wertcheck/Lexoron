"""OutboxService – verwaltet die Postausgang-Warteschlange (Prompt 25).

Siehe app/models/outbox_entry.py für die Grundregel: KEIN Codepfad in
diesem Service verschickt tatsächlich etwas. `mark_as_sent` bestätigt nur
lokal, dass der Anwalt AUSSERHALB dieses Systems versendet hat.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import AuditEvent, Draft, OutboxEntry


class OutboxEntryAlreadyExistsError(Exception):
    """Ein Draft darf nur EINEN Postausgang-Eintrag haben (siehe UNIQUE-
    Constraint auf `OutboxEntry.draft_id`)."""


class OutboxService:
    def add_to_outbox(self, draft: Draft, db: Session, *, actor: str) -> OutboxEntry:
        """Übergibt einen freigegebenen Entwurf an den Postausgang.

        Wird von der Web-Schicht direkt im Anschluss an
        `DraftFeedbackService.record_feedback(approved)` aufgerufen (siehe
        app/web/drafts_router.py: "Freigeben & Postausgang übergeben" ist
        EINE kombinierte Aktion, siehe Design-Referenz des Anwalts) - der
        Service selbst prüft NICHT den `Draft.status`, das bleibt
        Verantwortung des Aufrufers, um `DraftFeedbackService` nicht
        unnötig anzufassen (siehe Grundregel "keine unnötigen Umbauten").
        """
        existing = db.query(OutboxEntry).filter_by(draft_id=draft.id).first()
        if existing is not None:
            raise OutboxEntryAlreadyExistsError(
                f"Draft {draft.id} hat bereits einen Postausgang-Eintrag "
                f"({existing.id}, Status: {existing.status})"
            )

        entry = OutboxEntry(matter_id=draft.matter_id, draft_id=draft.id, status="pending")
        db.add(entry)
        db.flush()

        db.add(
            AuditEvent(
                entity_type="OutboxEntry",
                entity_id=entry.id,
                event_type="draft_added_to_outbox",
                actor=actor,
                details=f"Draft {draft.id} in den Postausgang übergeben",
            )
        )
        db.commit()
        db.refresh(entry)
        return entry

    def mark_as_sent(self, entry: OutboxEntry, db: Session, *, actor: str) -> OutboxEntry:
        """Bestätigt manuell, dass der Anwalt das Schreiben AUSSERHALB
        dieses Systems versendet hat. Löst selbst NICHTS aus - reine
        lokale Statuspflege + Audit-Eintrag."""
        if entry.status == "sent":
            raise ValueError(
                f"OutboxEntry {entry.id} ist bereits als versendet markiert "
                f"(am {entry.sent_at})"
            )

        entry.status = "sent"
        entry.sent_at = datetime.now(timezone.utc)
        entry.sent_by = actor

        db.add(
            AuditEvent(
                entity_type="OutboxEntry",
                entity_id=entry.id,
                event_type="draft_marked_sent",
                actor=actor,
                details=f"Als versendet markiert (Draft {entry.draft_id})",
            )
        )
        db.commit()
        db.refresh(entry)
        return entry
