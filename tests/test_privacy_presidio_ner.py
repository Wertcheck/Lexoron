"""Tests fuer app/privacy/presidio_ner.py.

Nutzt bewusst den ECHTEN Presidio-/spaCy-Stack (Praezedenzfall:
tests/test_search_embeddings_real_model.py fuer "echtes Modell, eigene
Testdatei") statt eines Fakes - hier wird gerade geprueft, ob die Presidio-
Integration selbst funktioniert, nicht nur der Aufrufcode drumherum.

CLAUDE.md-Pflicht: ausschliesslich synthetische Beispielsaetze, niemals
echte Mandantendaten."""

from app.privacy.presidio_ner import detect_presidio_entities


def test_detects_person_name_in_german_sentence() -> None:
    text = "Bitte kontaktieren Sie Herrn Dr. Thomas Weber bezüglich der Angelegenheit."

    spans = detect_presidio_entities(text)

    person_spans = [s for s in spans if s.category == "person"]
    assert person_spans
    assert any("Weber" in s.value for s in person_spans)


def test_detects_location() -> None:
    text = "Der Termin findet in Hamburg statt."

    spans = detect_presidio_entities(text)

    ort_spans = [s for s in spans if s.category == "ort"]
    assert any("Hamburg" in s.value for s in ort_spans)


def test_returns_detected_span_with_correct_positions() -> None:
    text = "Kontakt: Julia Neumann ist zuständig."

    spans = detect_presidio_entities(text)

    for span in spans:
        assert text[span.start : span.end] == span.value


def test_empty_text_returns_no_spans() -> None:
    assert detect_presidio_entities("") == []
    assert detect_presidio_entities("   ") == []


def test_common_german_formal_letter_produces_no_or_minimal_false_positives() -> None:
    """Regressionsschutz: Standard-Kanzleiformulierungen ohne echten
    Namen sollen nicht in grossem Umfang faelschlich als PERSON/ORT/
    ORGANISATION markiert werden (score_threshold in presidio_ner.py)."""
    sample = (
        "Sehr geehrte Damen und Herren,\n"
        "vielen Dank für Ihr Schreiben. Wir haben die Unterlagen geprüft "
        "und teilen Ihnen mit, dass der Einspruch gegen den Steuerbescheid "
        "form- und fristgerecht eingelegt wurde. Mit freundlichen Grüßen"
    )

    spans = detect_presidio_entities(sample)

    assert spans == []


def test_result_is_compatible_with_detected_span_interface() -> None:
    from app.privacy.detectors import DetectedSpan

    text = "Frau Sabine Klein aus München meldet sich."

    spans = detect_presidio_entities(text)

    assert all(isinstance(s, DetectedSpan) for s in spans)
