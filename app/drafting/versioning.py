"""create_new_draft_version – die EINZIGE Stelle im Projekt, die eine neue
`Draft`-Zeile anlegt.

GRUNDREGEL (Vorgabe des Anwalts, wörtlich): "Ein bestehender Entwurf darf
bei einer Neugenerierung nicht überschrieben werden" - und dasselbe gilt
für manuelle Änderungen. Diese Regel wird hier an EINER Stelle technisch
durchgesetzt, statt sie in drei verschiedenen Services (KI-Neugenerierung
in `app/drafting/service.py`, anwaltliche Bearbeitung in
`app/feedback/service.py`, zukünftige eigenständige Bearbeitungsaktion im
Dashboard) jeweils neu zu implementieren - jede Duplikation wäre ein
Risiko, dass eine Stelle versehentlich doch mutiert statt eine neue Zeile
anzulegen.

Jeder Aufruf:
1. Legt eine NEUE `Draft`-Zeile an (nie ein UPDATE auf eine bestehende).
2. Verkettet sie über `previous_version_id` (None nur bei der allerersten
   Version einer Entwurfslinie).
3. Erhöht `version` fortlaufend relativ zur Vorgängerversion.
4. Verändert die VORGÄNGER-Zeile an keiner Stelle - deren `content` und
   `status` bleiben eingefroren (Nachvollziehbarkeit der Historie).
5. Schreibt IMMER ein Audit-Event für die neue Version selbst
   (`event_type` vom Aufrufer vorgegeben, z. B. "draft_created" für v1,
   "draft_version_created" für alle Folgeversionen) - der Aufrufer kann
   zusätzlich eigene, spezifischere Audit-Events schreiben (z. B.
   "attorney_instruction_applied", "draft_manual_edit").
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditEvent, Draft


def create_new_draft_version(
    db: Session,
    *,
    matter_id: str,
    content: str,
    status: str = "draft",
    previous_draft: Draft | None = None,
    message_id: str | None = None,
    actor: str,
    event_type: str,
    details: str | None = None,
) -> Draft:
    """Legt eine neue, eigenständige Draft-Version an.

    `previous_draft=None` => allererste Version (v1) einer Entwurfslinie.
    `previous_draft=<Draft>` => Folgeversion, verkettet über
    `previous_version_id`; `message_id` wird dabei automatisch vom
    Vorgänger übernommen, falls nicht explizit angegeben.
    """
    if previous_draft is not None:
        version = previous_draft.version + 1
        previous_version_id = previous_draft.id
        if message_id is None:
            message_id = previous_draft.message_id
    else:
        version = 1
        previous_version_id = None

    draft = Draft(
        matter_id=matter_id,
        message_id=message_id,
        content=content,
        version=version,
        status=status,
        previous_version_id=previous_version_id,
    )
    db.add(draft)
    db.flush()

    db.add(
        AuditEvent(
            entity_type="Draft",
            entity_id=draft.id,
            event_type=event_type,
            actor=actor,
            details=details,
        )
    )
    db.commit()
    db.refresh(draft)
    return draft


def create_manual_edit_version(
    db: Session,
    *,
    previous_draft: Draft,
    new_content: str,
    status: str = "draft",
    actor: str,
    details: str | None = None,
) -> Draft:
    """Gemeinsamer Weg für JEDE manuelle Bearbeitung eines Entwurfs -
    egal ob über `DraftFeedbackService` (Bearbeitung im Rahmen einer
    Freigabe/"approved_with_edits") oder über eine eigenständige
    Dashboard-Bearbeitungsaktion (Prompt 23/24, ohne Freigabeentscheidung).

    Beide Aufrufer sollen exakt dieselbe Versionierungs- und Audit-Logik
    durchlaufen (zwei Audit-Events: das generische "draft_version_created"
    aus `create_new_draft_version` PLUS das spezifischere
    "draft_manual_edit" hier) - Zentralisierung verhindert, dass eine
    Stelle versehentlich abweicht (z. B. das spezifische Event vergisst).
    """
    new_draft = create_new_draft_version(
        db,
        matter_id=previous_draft.matter_id,
        content=new_content,
        status=status,
        previous_draft=previous_draft,
        actor=actor,
        event_type="draft_version_created",
        details=details,
    )
    db.add(
        AuditEvent(
            entity_type="Draft",
            entity_id=new_draft.id,
            event_type="draft_manual_edit",
            actor=actor,
            details=details,
        )
    )
    db.commit()
    db.refresh(new_draft)
    return new_draft
