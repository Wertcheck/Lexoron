"""KnowledgeItemService – Import, Versionierung, Freigabe, Deaktivierung.

Zustandsübergänge (siehe app/models/knowledge_item.py):
- Import -> immer `pending`, Version 1.
- Inhaltsänderung -> Version +1, Status zurück auf `pending` (jede
  Änderung erfordert erneute Freigabe - eine frühere Freigabe gilt NICHT
  automatisch für neuen Inhalt weiter).
- Freigabe -> `approved`, danach für die Suche indiziert
  (`DocumentSearchService.index_knowledge_item`, Prompt 11).
- Deaktivierung -> `deactivated`, verschwindet dadurch automatisch aus
  `search_knowledge_base()` (das filtert bereits auf `approved`), OHNE
  dass hier zusätzlich der Embedding-Eintrag gelöscht werden muss.

Volltext-/Versionshistorie (voller Diff über alle Versionen) ist bewusst
NICHT Teil dieses Prompts - analog zu `Draft.version` (Prompt 04/17) wird
nur die aktuelle Version gehalten; die Änderungshistorie ist über
`AuditEvent` grob nachvollziehbar (Version, Zeitpunkt), nicht als
vollständiger Inhalts-Diff.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.knowledge.schema import KnowledgeItemImport
from app.models import AuditEvent, KnowledgeItem


class KnowledgeItemService:
    def __init__(self, search_service=None) -> None:
        # Optional, damit dieser Service auch ohne Suchschicht (z. B. in
        # isolierten Tests) nutzbar ist. Typ bewusst nicht importiert, um
        # keine harte Abhaengigkeit von app.search auf Modulebene zu
        # erzwingen (vermeidet Zirkularimporte, falls app.search spaeter
        # etwas aus app.knowledge braucht).
        self.search_service = search_service

    def import_item(
        self, data: KnowledgeItemImport, db: Session, *, actor: str = "system"
    ) -> KnowledgeItem:
        item = KnowledgeItem(
            title=data.title,
            content=data.content,
            category=data.category,
            practice_area=data.practice_area,
            source=data.source,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
        )
        db.add(item)
        db.flush()

        db.add(
            AuditEvent(
                entity_type="KnowledgeItem",
                entity_id=item.id,
                event_type="knowledge_item_imported",
                actor=actor,
                details=f"Importiert: '{data.title}' (Version 1, Status: pending)",
            )
        )
        db.commit()
        db.refresh(item)
        return item

    def update_content(
        self, item: KnowledgeItem, new_content: str, db: Session, *, actor: str
    ) -> KnowledgeItem:
        if not new_content or not new_content.strip():
            raise ValueError("new_content darf nicht leer sein")

        old_version = item.version
        item.content = new_content
        item.version += 1
        # Erneute Freigabe zwingend erforderlich - eine Freigabe des alten
        # Inhalts gilt NICHT automatisch fuer den neuen Inhalt weiter.
        item.approval_status = "pending"

        db.add(
            AuditEvent(
                entity_type="KnowledgeItem",
                entity_id=item.id,
                event_type="knowledge_item_content_updated",
                actor=actor,
                details=(
                    f"Version {old_version} -> {item.version}. Status auf "
                    "'pending' zurückgesetzt - erneute Freigabe erforderlich."
                ),
            )
        )
        db.commit()
        db.refresh(item)
        return item

    def approve(
        self, item: KnowledgeItem, db: Session, *, actor: str
    ) -> KnowledgeItem:
        item.approval_status = "approved"
        db.add(
            AuditEvent(
                entity_type="KnowledgeItem",
                entity_id=item.id,
                event_type="knowledge_item_approved",
                actor=actor,
                details=f"Freigegeben (Version {item.version})",
            )
        )
        db.commit()
        db.refresh(item)

        if self.search_service is not None:
            self.search_service.index_knowledge_item(item, db)

        return item

    def deactivate(
        self, item: KnowledgeItem, db: Session, *, actor: str, reason: str
    ) -> KnowledgeItem:
        if not reason or not reason.strip():
            raise ValueError(
                "reason darf nicht leer sein - Deaktivierung muss "
                "nachvollziehbar begründet werden"
            )

        item.approval_status = "deactivated"
        db.add(
            AuditEvent(
                entity_type="KnowledgeItem",
                entity_id=item.id,
                event_type="knowledge_item_deactivated",
                actor=actor,
                details=reason,
            )
        )
        db.commit()
        db.refresh(item)
        return item

    def list_items(
        self,
        db: Session,
        *,
        category: str | None = None,
        practice_area: str | None = None,
        approval_status: str | None = None,
        only_currently_valid: bool = False,
        reference_date: date | None = None,
    ) -> list[KnowledgeItem]:
        """Metadatenbasiertes Auflisten/Filtern - für Verwaltung/Dashboard
        (Prompt 22), unabhängig von der semantischen Suche aus Prompt 11."""
        query = db.query(KnowledgeItem)
        if category is not None:
            query = query.filter(KnowledgeItem.category == category)
        if practice_area is not None:
            query = query.filter(KnowledgeItem.practice_area == practice_area)
        if approval_status is not None:
            query = query.filter(KnowledgeItem.approval_status == approval_status)

        items = query.all()

        if only_currently_valid:
            check_date = reference_date or date.today()
            items = [item for item in items if self._is_valid_on(item, check_date)]

        return items

    @staticmethod
    def _is_valid_on(item: KnowledgeItem, on_date: date) -> bool:
        if item.valid_from is not None and on_date < item.valid_from:
            return False
        if item.valid_until is not None and on_date > item.valid_until:
            return False
        return True
