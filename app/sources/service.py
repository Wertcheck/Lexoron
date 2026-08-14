"""SourceService – Import, Freigabe, Als-veraltet-Markierung, Filterung.

Zustandsübergänge (`Source.approval_level`, siehe app/models/source.py):
- Import -> immer `entwurf`.
- Freigabe -> `freigegeben` (erst ab hier sollte die Quelle in Prompt 15
  für Recherche/Entwürfe herangezogen werden - diese Verknüpfung entsteht
  erst dort, analog zu KnowledgeItem/Prompt 12).
- Als veraltet markieren -> `veraltet`, verlangt eine Begründung (analog
  zu `KnowledgeItemService.deactivate`, Prompt 12) - eine Quelle
  verschwindet dadurch NICHT aus der Datenbank (Nachvollziehbarkeit für
  frühere Vorgänge bleibt erhalten, siehe ARCHITECTURE.md §13
  "Rechtsaktualität": ein späteres Update darf nicht die historische
  Beurteilung eines alten Vorgangs überschreiben).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import AuditEvent, Source
from app.sources.provider import ManualSourceProvider, SourceProvider
from app.sources.schema import SourceImport


class SourceService:
    def __init__(
        self, provider: SourceProvider | None = None, search_service=None
    ) -> None:
        self.provider = provider or ManualSourceProvider()
        # Optional wie bei KnowledgeItemService - vermeidet harte
        # Abhaengigkeit von app.search auf Modulebene.
        self.search_service = search_service

    def import_source(
        self, data: SourceImport, db: Session, *, actor: str
    ) -> Source:
        resolved = self.provider.resolve(data)

        source = Source(
            title=resolved.title,
            source_type=resolved.source_type,
            reference=resolved.reference,
            url=resolved.url,
            document_date=resolved.document_date,
            retrieved_at=resolved.retrieved_at or date.today(),
            valid_from=resolved.valid_from,
            valid_until=resolved.valid_until,
            notes=resolved.notes,
            provider_name=self.provider.name,
        )
        db.add(source)
        db.flush()

        db.add(
            AuditEvent(
                entity_type="Source",
                entity_id=source.id,
                event_type="source_imported",
                actor=actor,
                details=(
                    f"Importiert: '{resolved.title}' ({resolved.source_type}), "
                    f"Provider: {self.provider.name}, Status: entwurf"
                ),
            )
        )
        db.commit()
        db.refresh(source)
        return source

    def approve_source(self, source: Source, db: Session, *, actor: str) -> Source:
        source.approval_level = "freigegeben"
        db.add(
            AuditEvent(
                entity_type="Source",
                entity_id=source.id,
                event_type="source_approved",
                actor=actor,
                details="Rechtsquelle freigegeben",
            )
        )
        db.commit()
        db.refresh(source)

        if self.search_service is not None:
            self.search_service.index_source(source, db)

        return source

    def mark_outdated(
        self, source: Source, db: Session, *, actor: str, reason: str
    ) -> Source:
        if not reason or not reason.strip():
            raise ValueError(
                "reason darf nicht leer sein - Als-veraltet-Markierung muss "
                "nachvollziehbar begründet werden"
            )

        source.approval_level = "veraltet"
        db.add(
            AuditEvent(
                entity_type="Source",
                entity_id=source.id,
                event_type="source_marked_outdated",
                actor=actor,
                details=reason,
            )
        )
        db.commit()
        db.refresh(source)
        return source

    def list_sources(
        self,
        db: Session,
        *,
        source_type: str | None = None,
        approval_level: str | None = None,
        only_currently_valid: bool = False,
        reference_date: date | None = None,
    ) -> list[Source]:
        query = db.query(Source)
        if source_type is not None:
            query = query.filter(Source.source_type == source_type)
        if approval_level is not None:
            query = query.filter(Source.approval_level == approval_level)

        sources = query.all()

        if only_currently_valid:
            check_date = reference_date or date.today()
            sources = [s for s in sources if self._is_valid_on(s, check_date)]

        return sources

    @staticmethod
    def _is_valid_on(source: Source, on_date: date) -> bool:
        if source.valid_from is not None and on_date < source.valid_from:
            return False
        if source.valid_until is not None and on_date > source.valid_until:
            return False
        return True
