"""DeadlineAnalysisService – erzeugt `Deadline`-Datensätze aus einem Dokument.

Setzt auf `Document.extracted_text` (Prompt 06) UND `Document.matter_id`
(Prompt 09) auf - eine Frist kann nur einer Akte zugeordnet werden, wenn
das Dokument bereits einer Akte zugeordnet ist (`Deadline.matter_id` ist
nicht nullable, siehe app/models/deadline.py). Ohne Text oder ohne
Aktenzuordnung wird die Analyse übersprungen und protokolliert, statt
Annahmen zu treffen.

`review_status` wird NIE von diesem Service gesetzt/verändert - der
Deadline-Modell-Default "unreviewed" (Prompt 04) bleibt für jede hier
erzeugte Frist bestehen, bis ein Mensch sie bestätigt oder verwirft.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.deadlines.extractor import DeadlineExtractor
from app.models import AuditEvent, Deadline, Document


class DeadlineAnalysisService:
    def __init__(self, extractor: DeadlineExtractor) -> None:
        self.extractor = extractor

    def analyze_document(self, document: Document, db: Session) -> list[Deadline]:
        if not document.extracted_text or not document.extracted_text.strip():
            db.add(
                AuditEvent(
                    entity_type="Document",
                    entity_id=document.id,
                    event_type="deadline_analysis_skipped",
                    actor="system",
                    details="Kein extrahierter Text vorhanden",
                )
            )
            db.commit()
            return []

        if not document.matter_id:
            db.add(
                AuditEvent(
                    entity_type="Document",
                    entity_id=document.id,
                    event_type="deadline_analysis_skipped",
                    actor="system",
                    details=(
                        "Dokument noch keiner Akte zugeordnet - "
                        "Fristenanalyse erfordert eine Aktenzuordnung"
                    ),
                )
            )
            db.commit()
            return []

        extracted = self.extractor.extract(document.extracted_text)
        created_deadlines: list[Deadline] = []

        for candidate in extracted:
            # review_status wird bewusst NICHT gesetzt - Modell-Default
            # "unreviewed" greift, siehe Moduldocstring.
            deadline = Deadline(
                matter_id=document.matter_id,
                document_id=document.id,
                source_text=f"{candidate.raw_date_text} :: {candidate.source_text}",
                due_date=candidate.due_date,
                confidence=candidate.confidence,
            )
            db.add(deadline)
            created_deadlines.append(deadline)

        db.add(
            AuditEvent(
                entity_type="Document",
                entity_id=document.id,
                event_type="deadline_analysis_completed",
                actor="system",
                details=(
                    f"{len(created_deadlines)} möglicher Frist(en) gefunden, "
                    "alle mit Status 'unreviewed' - manuelle Prüfung erforderlich"
                ),
            )
        )
        db.commit()
        for deadline in created_deadlines:
            db.refresh(deadline)
        return created_deadlines
