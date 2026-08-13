"""Textextraktion aus PDFs und gängigen Office-Dokumenten.

Bewusst rein technisch: liest vorhandenen Text aus, ohne ihn zu bewerten,
zu kürzen oder zu interpretieren. Erkennt lediglich, ob genug Text
vorhanden ist oder ob OCR nötig sein könnte (Entscheidung darüber trifft
`app/documents/service.py`, nicht dieses Modul).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf
from docx import Document as DocxDocument

# Dateiendungen, aus denen direkt Text extrahiert werden kann (ggf. leer,
# dann evtl. OCR-Kandidat).
SUPPORTED_TEXT_EXTENSIONS = {".pdf", ".docx", ".txt"}
# Dateiendungen, die direkt als Bild gelten und nie eigenen extrahierbaren
# Text haben - immer OCR-Kandidat, falls OCR aktiviert ist.
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


@dataclass
class ExtractionResult:
    text: str | None
    # True, wenn kein/zu wenig Text gefunden wurde und die Datei ein
    # Format ist, aus dem OCR grundsätzlich Sinn ergeben könnte.
    needs_ocr: bool
    # True, wenn das Dateiformat von diesem Modul gar nicht unterstützt
    # wird (weder Text noch OCR möglich) - z. B. ein unbekanntes Format.
    unsupported_format: bool = False


def _extract_pdf_text(path: Path) -> str:
    text_parts: list[str] = []
    with pymupdf.open(path) as pdf:
        for page in pdf:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def _extract_docx_text(path: Path) -> str:
    docx_document = DocxDocument(str(path))
    return "\n".join(paragraph.text for paragraph in docx_document.paragraphs)


def _extract_txt_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_text(
    path: Path, *, min_text_length: int = 20
) -> ExtractionResult:
    """Extrahiert Text aus einer Datei, falls das Format unterstützt wird.

    `min_text_length` steuert, ab wann extrahierter Text als "ausreichend"
    gilt statt als OCR-Kandidat (z. B. verhindert das, dass ein PDF mit nur
    einer eingebetteten Kopfzeile fälschlich als vollständig erfasst gilt).
    """
    suffix = path.suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        return ExtractionResult(text=None, needs_ocr=True)

    if suffix not in SUPPORTED_TEXT_EXTENSIONS:
        return ExtractionResult(text=None, needs_ocr=False, unsupported_format=True)

    if suffix == ".pdf":
        text = _extract_pdf_text(path)
    elif suffix == ".docx":
        text = _extract_docx_text(path)
    else:  # .txt
        text = _extract_txt_text(path)

    stripped = text.strip()
    if len(stripped) < min_text_length:
        # Nur PDFs koennen sinnvoll per OCR nachbearbeitet werden (Seiten
        # lassen sich rastern) - ein leeres .docx/.txt ist kein OCR-Fall.
        needs_ocr = suffix == ".pdf"
        return ExtractionResult(text=text or None, needs_ocr=needs_ocr)

    return ExtractionResult(text=text, needs_ocr=False)
