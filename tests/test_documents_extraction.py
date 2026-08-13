"""Tests fuer app/documents/extraction.py (Prompt 06).

Nutzt die synthetischen Testdateien aus tests/fixtures/ - keine echten
Mandantendaten."""

from pathlib import Path

from app.documents.extraction import extract_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_pdf_with_real_text_layer_is_extracted_directly() -> None:
    result = extract_text(FIXTURES / "text_document.pdf")

    assert result.needs_ocr is False
    assert result.unsupported_format is False
    assert result.text is not None
    assert "Synthetisches Testschreiben" in result.text


def test_scanned_pdf_without_text_layer_needs_ocr() -> None:
    result = extract_text(FIXTURES / "scanned_document.pdf")

    assert result.needs_ocr is True
    assert result.unsupported_format is False


def test_empty_pdf_needs_ocr() -> None:
    result = extract_text(FIXTURES / "empty_document.pdf")

    assert result.needs_ocr is True


def test_docx_with_text_is_extracted_directly() -> None:
    result = extract_text(FIXTURES / "text_document.docx")

    assert result.needs_ocr is False
    assert result.text is not None
    assert "Word-Dokument" in result.text


def test_image_file_always_needs_ocr_directly() -> None:
    result = extract_text(FIXTURES / "scanned_image.png")

    assert result.needs_ocr is True
    assert result.text is None
    assert result.unsupported_format is False


def test_unsupported_format_is_flagged_without_crashing() -> None:
    result = extract_text(FIXTURES / "unbekannt.xyz")

    assert result.unsupported_format is True
    assert result.needs_ocr is False
    assert result.text is None


def test_min_text_length_threshold_is_respected(tmp_path: Path) -> None:
    """Ein PDF mit nur sehr wenig Text (z. B. einzelnes Wort) soll bei
    ausreichend hoher Schwelle trotzdem als OCR-Kandidat gelten."""
    import pymupdf

    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Kurz")
    short_pdf_path = tmp_path / "kurz.pdf"
    pdf.save(short_pdf_path)
    pdf.close()

    result_strict = extract_text(short_pdf_path, min_text_length=100)
    assert result_strict.needs_ocr is True

    result_lenient = extract_text(short_pdf_path, min_text_length=1)
    assert result_lenient.needs_ocr is False
