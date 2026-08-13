"""Tests fuer app/documents/ocr.py (Prompt 06).

Nutzt echte Tesseract-Ausfuehrung gegen synthetische Testbilder/-PDFs -
keine Mocks, da genau das Verhalten zaehlt, das im produktiven Einsatz
zum Tragen kommt. Toleriert kleine OCR-Ungenauigkeiten (z. B. bei eng
gesetzter Schrift), prueft aber auf klar erkennbare Kernbestandteile.
"""

from pathlib import Path

import pytest

from app.documents.ocr import OcrError, run_ocr

FIXTURES = Path(__file__).parent / "fixtures"


def test_ocr_recognizes_text_in_scanned_pdf() -> None:
    text = run_ocr(FIXTURES / "scanned_document.pdf")
    normalized = text.upper()

    assert "TESTTEXT" in normalized


def test_ocr_recognizes_text_in_image_file() -> None:
    text = run_ocr(FIXTURES / "scanned_image.png")
    normalized = text.upper()

    assert "TESTTEXT" in normalized


def test_ocr_raises_for_unsupported_format() -> None:
    with pytest.raises(OcrError):
        run_ocr(FIXTURES / "unbekannt.xyz")


def test_ocr_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(OcrError):
        run_ocr(tmp_path / "existiert_nicht.pdf")
