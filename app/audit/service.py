"""AuditLogService – lesender Zugriff auf das bereits bestehende
Audit-Log (`AuditEvent`, Prompt 04).

Wichtigste Methode: `list_events_for_matter` - da `AuditEvent` generisch
per `entity_type`/`entity_id` funktioniert (nicht direkt per `matter_id`),
muss der Service dafuer erst alle zu einer Akte gehoerenden Entitaeten
(Dokumente, Nachrichten, Fristen, Entwuerfe, Aufgaben, Workflow-Laeufe)
ermitteln und dann deren Ereignisse zusammenfuehren. Rein lesend - erzeugt
selbst niemals neue Audit-Events.

WICHTIG (Aktenisolation): `list_events_for_matter` fragt ausschliesslich
Entitaeten ab, die tatsaechlich zu der uebergebenen `matter_id` gehoeren -
exakt dasselbe Muster wie ueberall sonst im Projekt (z. B.
`search_within_matter`, `PromptContextBuilder`).

Bewusst NICHT eingeschlossen: `KnowledgeItem`, `Source`, `Policy` - das
sind kanzleiweite, nicht aktenbezogene Ressourcen (siehe Konzept §5/§6),
ihre Audit-Events gehoeren folgerichtig nicht in eine Akten-Historie.
"""

from __future__ import annotations

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import (
    AttorneyInstruction,
    AuditEvent,
    Deadline,
    Document,
    Draft,
    Message,
    Task,
    WorkflowRun,
)

# (SQLAlchemy-Modell, entity_type-String) - der entity_type-String muss
# exakt dem entsprechen, was die jeweiligen Services beim Schreiben von
# AuditEvents verwenden (z. B. entity_type="Document").
_MATTER_SCOPED_MODELS: tuple[tuple[type, str], ...] = (
    (Document, "Document"),
    (Message, "Message"),
    (Deadline, "Deadline"),
    (Draft, "Draft"),
    (Task, "Task"),
    (WorkflowRun, "WorkflowRun"),
    # Ergaenzt Prompt 24: AttorneyInstruction (Prompt 23) hatte bislang
    # KEINEN Eintrag hier - ihre Audit-Events (attorney_instruction_created/
    # _applied) waren dadurch bei einer aktenweiten Abfrage unsichtbar,
    # obwohl das Modell bereits matter_id trägt. Echte Luecke, jetzt
    # geschlossen.
    (AttorneyInstruction, "AttorneyInstruction"),
)


class AuditLogService:
    def list_events_for_entity(
        self, entity_type: str, entity_id: str, db: Session
    ) -> list[AuditEvent]:
        return (
            db.query(AuditEvent)
            .filter_by(entity_type=entity_type, entity_id=entity_id)
            .order_by(AuditEvent.created_at)
            .all()
        )

    def list_events_for_matter(self, matter_id: str, db: Session) -> list[AuditEvent]:
        if not matter_id:
            raise ValueError(
                "matter_id ist erforderlich - Audit-Abfrage ohne Aktenbezug "
                "ist nicht erlaubt"
            )

        # Die Akte selbst kann ebenfalls direktes Ziel eines AuditEvents
        # sein (z. B. "legal_research_performed", entity_type="Matter").
        entity_pairs: list[tuple[str, str]] = [("Matter", matter_id)]

        for model, type_name in _MATTER_SCOPED_MODELS:
            ids = (
                db.query(model.id)
                .filter(model.matter_id == matter_id)
                .all()
            )
            entity_pairs.extend((type_name, row[0]) for row in ids)

        if not entity_pairs:
            return []

        conditions = [
            and_(AuditEvent.entity_type == t, AuditEvent.entity_id == i)
            for t, i in entity_pairs
        ]
        return (
            db.query(AuditEvent)
            .filter(or_(*conditions))
            .order_by(AuditEvent.created_at)
            .all()
        )
