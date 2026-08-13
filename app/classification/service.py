"""ClassificationService – wendet einen `DocumentClassifier` auf ein
`Document` an und persistiert das Ergebnis.

Setzt auf `Document.extracted_text` (Prompt 06) auf. Ohne extrahierten
Text erfolgt KEINE Klassifikation - wird übersprungen und entsprechend
protokolliert, statt mit leerem/geratenem Ergebnis fortzufahren.

Speichert zusätzlich, ob die Konfidenz unter der konfigurierten Schwelle
liegt (`classification_low_confidence_threshold`) - das ist die Grundlage
dafür, dass Prompt 09 (Aktenzuordnung) bei niedriger Konfidenz NICHT
automatisch zuordnen darf.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.classification.classifier import DocumentClassifier
from app.models import AuditEvent, Document


class ClassificationService:
    def __init__(
        self, classifier: DocumentClassifier, *, low_confidence_threshold: float
    ) -> None:
        self.classifier = classifier
        self.low_confidence_threshold = low_confidence_threshold

    def classify_document(self, document: Document, db: Session) -> Document:
        if not document.extracted_text or not document.extracted_text.strip():
            db.add(
                AuditEvent(
                    entity_type="Document",
                    entity_id=document.id,
                    event_type="document_classification_skipped",
                    actor="system",
                    details="Kein extrahierter Text vorhanden (OCR ggf. noch ausstehend)",
                )
            )
            db.commit()
            db.refresh(document)
            return document

        result = self.classifier.classify(
            document.extracted_text, filename=document.original_filename
        )
        needs_review = result.requires_manual_review(self.low_confidence_threshold)

        document.classified_type = result.document_type
        document.classification_confidence = result.confidence
        document.classification_reasoning = result.reasoning
        document.classification_topic = result.topic
        document.classification_action_required = result.action_required
        document.classification_result_json = json.dumps(
            result.model_dump(), ensure_ascii=False
        )

        db.add(
            AuditEvent(
                entity_type="Document",
                entity_id=document.id,
                event_type="document_classified",
                actor="system",
                details=(
                    f"Typ: {result.document_type}, Konfidenz: {result.confidence:.2f}, "
                    f"manuelle Prüfung erforderlich: {needs_review}"
                ),
            )
        )
        db.commit()
        db.refresh(document)
        return document
