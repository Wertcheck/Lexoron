"""DocumentProcessingService – Orchestrierung von Textextraktion und OCR.

Ablauf pro `Document` (Konzept §3, Schritt 3 "Extraktion"):
1. Versuche direkte Textextraktion (PDF/DOCX/TXT).
2. Falls kein/zu wenig Text gefunden wurde UND `settings.ocr_enabled=True`
   ist: OCR ausführen.
3. Falls kein Text gefunden wurde UND OCR deaktiviert ist: Status bleibt
   "pending" (wartet auf manuelle Aktivierung/spätere Verarbeitung) -
   niemals stillschweigend als erledigt markieren.
4. `extracted_text`/`ocr_status` werden aktualisiert - `file_path`
   (Original) bleibt unverändert (siehe app/models/document.py).

Enthält bewusst KEINE juristische Interpretation - reine technische
Extraktion. Klassifikation und Aktenzuordnung folgen in Prompt 08/09.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.documents.extraction import extract_text
from app.documents.ocr import OcrError, configure_tesseract, run_ocr
from app.models import AuditEvent, Document


class DocumentProcessingService:
    def __init__(
        self,
        *,
        ocr_enabled: bool,
        ocr_languages: str = "deu+eng",
        min_extracted_text_length: int = 20,
        tesseract_cmd: str | None = None,
    ) -> None:
        self.ocr_enabled = ocr_enabled
        self.ocr_languages = ocr_languages
        self.min_extracted_text_length = min_extracted_text_length
        configure_tesseract(tesseract_cmd)

    def process_document(self, document: Document, db: Session) -> Document:
        """Verarbeitet ein einzelnes Document: Extraktion + ggf. OCR.

        Aktualisiert `document.extracted_text` und `document.ocr_status`
        in-place, schreibt ein begleitendes `AuditEvent` und committet die
        Änderung. Gibt das aktualisierte Document zurück.
        """
        path = Path(document.file_path)
        result = extract_text(path, min_text_length=self.min_extracted_text_length)

        if result.unsupported_format:
            document.ocr_status = "unsupported_format"
            event_type = "document_format_unsupported"
            details = f"Dateiformat nicht unterstützt: {path.suffix}"
        elif not result.needs_ocr:
            document.extracted_text = result.text
            document.ocr_status = "not_needed"
            event_type = "document_text_extracted"
            details = "Text direkt extrahiert, kein OCR erforderlich"
        elif not self.ocr_enabled:
            document.ocr_status = "pending"
            event_type = "document_ocr_pending"
            details = "OCR erforderlich, aber OCR ist deaktiviert (OCR_ENABLED=false)"
        else:
            try:
                ocr_text = run_ocr(path, languages=self.ocr_languages)
            except OcrError as exc:
                document.ocr_status = "failed"
                event_type = "document_ocr_failed"
                details = str(exc)
            else:
                document.extracted_text = ocr_text
                document.ocr_status = "done"
                event_type = "document_ocr_completed"
                details = f"OCR erfolgreich ({self.ocr_languages})"

        db.add(
            AuditEvent(
                entity_type="Document",
                entity_id=document.id,
                event_type=event_type,
                actor="system",
                details=details,
            )
        )
        db.commit()
        db.refresh(document)
        return document
