"""Dokumentverarbeitung (Prompt 06: Text-/OCR-Extraktion).

Erfasst Text aus PDFs und gängigen Office-Dokumenten; löst bei fehlendem
Text einen konfigurierbaren OCR-Schritt aus. Enthält bewusst KEINE
juristische Interpretation - nur technische Extraktion, Original/Text/
Metadaten bleiben strikt getrennt (siehe app/models/document.py).
"""

from app.documents.service import DocumentProcessingService

__all__ = ["DocumentProcessingService"]
