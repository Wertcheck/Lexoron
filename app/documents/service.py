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

Seit Prompt 31: ein OCR-Fehlschlag wird zusätzlich im Fehler-/Retry-
System (app/errors/) protokolliert - vorher blieb `ocr_status="failed"`
ein Endzustand ohne jeden Weg, es erneut zu versuchen, außer den
Datensatz manuell zu löschen und neu anzulegen. `RetryService` wird
bewusst als DEFAULT-Parameter injiziert (nicht hart codiert), damit
Aufrufer (z. B. Tests) eine eigene Instanz übergeben können.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.documents.extraction import extract_text
from app.documents.ocr import OcrError, configure_tesseract, run_ocr
from app.errors.service import RetryService
from app.models import AuditEvent, Document


class DocumentProcessingService:
    def __init__(
        self,
        *,
        ocr_enabled: bool,
        ocr_languages: str = "deu+eng",
        min_extracted_text_length: int = 20,
        tesseract_cmd: str | None = None,
        retry_service: RetryService | None = None,
    ) -> None:
        self.ocr_enabled = ocr_enabled
        self.ocr_languages = ocr_languages
        self.min_extracted_text_length = min_extracted_text_length
        self.retry_service = retry_service or RetryService()
        configure_tesseract(tesseract_cmd)

    def process_document(
        self, document: Document, db: Session, *, actor: str = "system"
    ) -> Document:
        """Verarbeitet ein einzelnes Document: Extraktion + ggf. OCR.

        Aktualisiert `document.extracted_text` und `document.ocr_status`
        in-place, schreibt ein begleitendes `AuditEvent` und committet die
        Änderung. Gibt das aktualisierte Document zurück.

        `actor` (Prompt 31): erlaubt, einen manuell ausgelösten Retry
        (z. B. über das Dashboard) im Audit-Log dem tatsächlich
        handelnden Nutzer zuzuordnen, statt pauschal "system" - Standard
        bleibt "system" für die automatische Erstverarbeitung.
        """
        path = Path(document.file_path)
        try:
            result = extract_text(path, min_text_length=self.min_extracted_text_length)
        except Exception as exc:  # noqa: BLE001 - kontrolliert ins Fehler-/Retry-System überführen
            # SICHERHEITSKRITISCH + ROBUSTHEIT (Prompt 31, gefunden bei der
            # Absicherung des Fehler-/Retry-Systems): `extract_text` selbst
            # war NICHT gegen eine fehlende/unlesbare/beschädigte Datei
            # abgesichert - ein `FileNotFoundError` o. Ä. hätte die gesamte
            # Dokumentverarbeitung unkontrolliert abstürzen lassen, statt
            # dem gerade gebauten Fehler-/Retry-System übergeben zu werden.
            # Wie beim OCR-Fehlerpfad: NUR der Exception-TYP, niemals die
            # Original-Nachricht (kann den Dateipfad/-namen enthalten).
            document.ocr_status = "failed"
            event_type = "document_ocr_failed"
            details = f"Textextraktion fehlgeschlagen: {type(exc).__name__}"
            self.retry_service.record_failure(
                db,
                entity_type="Document",
                entity_id=document.id,
                operation="ocr",
                error_category="transient",
                error_message=details,
                actor=actor,
            )
            db.add(
                AuditEvent(
                    entity_type="Document",
                    entity_id=document.id,
                    event_type=event_type,
                    actor=actor,
                    details=details,
                )
            )
            db.commit()
            db.refresh(document)
            return document

        if result.unsupported_format:
            document.ocr_status = "unsupported_format"
            event_type = "document_format_unsupported"
            details = f"Dateiformat nicht unterstützt: {path.suffix}"
        elif not result.needs_ocr:
            document.extracted_text = result.text
            document.ocr_status = "not_needed"
            event_type = "document_text_extracted"
            details = "Text direkt extrahiert, kein OCR erforderlich"
            self.retry_service.record_success(
                db, entity_type="Document", entity_id=document.id, operation="ocr", actor=actor
            )
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
                # Bewusst NUR die technische Fehlermeldung - niemals
                # Dokumentinhalt (siehe app/errors/models.py Grundregel).
                details = str(exc)
                self.retry_service.record_failure(
                    db,
                    entity_type="Document",
                    entity_id=document.id,
                    operation="ocr",
                    # OCR-Fehlschläge sind meist Umgebungsprobleme
                    # (Tesseract nicht erreichbar, temporäre Ressourcen-
                    # Engpässe) - als "transient" eingestuft, damit ein
                    # automatischer Wiederholungsversuch sinnvoll ist.
                    error_category="transient",
                    error_message=details,
                    actor=actor,
                )
            else:
                document.extracted_text = ocr_text
                document.ocr_status = "done"
                event_type = "document_ocr_completed"
                details = f"OCR erfolgreich ({self.ocr_languages})"
                self.retry_service.record_success(
                    db,
                    entity_type="Document",
                    entity_id=document.id,
                    operation="ocr",
                    actor=actor,
                )

        db.add(
            AuditEvent(
                entity_type="Document",
                entity_id=document.id,
                event_type=event_type,
                actor=actor,
                details=details,
            )
        )
        db.commit()
        db.refresh(document)
        return document
