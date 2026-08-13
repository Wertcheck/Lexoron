"""OCR-Verarbeitung (Tesseract).

Wird nur aufgerufen, wenn `settings.ocr_enabled=True` ist (Entscheidung
liegt beim aufrufenden Service, nicht hier). Für PDFs werden die Seiten
gerastert (über PyMuPDF, kein zusätzliches externes Tool wie Poppler
nötig) und einzeln per Tesseract erkannt; für Bilddateien direkt.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image

from app.documents.extraction import IMAGE_EXTENSIONS


class OcrError(Exception):
    """Fehler während der OCR-Verarbeitung (z. B. Tesseract nicht
    gefunden/nicht ausführbar). Wird bewusst als eigene Exception-Klasse
    geführt, damit der aufrufende Service den Dokumentstatus korrekt auf
    "failed" statt "done" setzen kann."""


def configure_tesseract(tesseract_cmd: str | None) -> None:
    """Setzt einen expliziten Pfad zur Tesseract-Programmdatei, falls
    konfiguriert (z. B. unter Windows, wo Tesseract oft nicht automatisch
    im PATH liegt)."""
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def run_ocr(path: Path, *, languages: str = "deu+eng", dpi: int = 200) -> str:
    """Führt OCR auf einer Datei aus und gibt den erkannten Text zurück.

    Wirft `OcrError`, wenn die Datei weder als PDF noch als unterstütztes
    Bildformat erkannt wird, oder wenn Tesseract selbst fehlschlägt.
    """
    suffix = path.suffix.lower()

    try:
        if suffix == ".pdf":
            return _run_ocr_on_pdf(path, languages=languages, dpi=dpi)
        if suffix in IMAGE_EXTENSIONS:
            return _run_ocr_on_image(path, languages=languages)
    except Exception as exc:  # noqa: BLE001 - in OcrError kapseln
        raise OcrError(f"OCR fehlgeschlagen für {path}: {exc}") from exc

    raise OcrError(f"OCR wird für dieses Dateiformat nicht unterstützt: {path}")


def _run_ocr_on_pdf(path: Path, *, languages: str, dpi: int) -> str:
    text_parts: list[str] = []
    with pymupdf.open(path) as pdf:
        for page in pdf:
            pixmap = page.get_pixmap(dpi=dpi)
            image = Image.frombytes(
                "RGB", (pixmap.width, pixmap.height), pixmap.samples
            )
            text_parts.append(pytesseract.image_to_string(image, lang=languages))
    return "\n".join(text_parts)


def _run_ocr_on_image(path: Path, *, languages: str) -> str:
    with Image.open(path) as image:
        return pytesseract.image_to_string(image, lang=languages)
