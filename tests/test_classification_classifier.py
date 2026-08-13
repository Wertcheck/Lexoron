"""Tests fuer app/classification/classifier.py (Prompt 08).

Nutzt ausschliesslich synthetische Testtexte - keine echten
Mandantendaten."""

from app.classification.classifier import PlaceholderDocumentClassifier

classifier = PlaceholderDocumentClassifier()


def test_recognizes_rechnung_by_keyword() -> None:
    result = classifier.classify("Sehr geehrte Damen und Herren, anbei unsere Rechnung Nr. 123.")
    assert result.document_type == "Rechnung"


def test_recognizes_vollmacht_by_keyword() -> None:
    result = classifier.classify("Hiermit erteile ich Ihnen Vollmacht in dieser Angelegenheit.")
    assert result.document_type == "Vollmacht"


def test_recognizes_kuendigung_by_keyword() -> None:
    result = classifier.classify("Hiermit kündige ich den Vertrag fristgerecht.")
    assert result.document_type == "Kündigungsschreiben"


def test_unrecognized_text_is_unbekannt() -> None:
    result = classifier.classify("Ein völlig neutraler Testsatz ohne besondere Begriffe.")
    assert result.document_type == "Unbekannt"


def test_confidence_is_always_low_for_placeholder() -> None:
    """Der Platzhalter darf NIE hochsicher wirken - unabhaengig vom Text."""
    texts = [
        "Rechnung Vollmacht Kündigung Mahnung Klage Gericht Vertrag",
        "Ein völlig neutraler Testsatz.",
        "",
    ]
    for text in texts:
        result = classifier.classify(text)
        assert result.confidence <= 0.4


def test_detects_action_required_keyword() -> None:
    result = classifier.classify("Bitte antworten Sie dringend bis zum 15.03.")
    assert result.action_required is True


def test_no_action_required_without_keyword() -> None:
    result = classifier.classify("Ein ganz normales Schreiben ohne Eile.")
    assert result.action_required is False


def test_detects_possible_matter_reference() -> None:
    result = classifier.classify("Bezug: Az.: 123/24, Ihr Schreiben vom 01.02.")
    assert result.possible_matter_reference == "123/24"


def test_no_matter_reference_when_absent() -> None:
    result = classifier.classify("Ein Schreiben ganz ohne Aktenzeichen.")
    assert result.possible_matter_reference is None


def test_reasoning_mentions_placeholder_nature() -> None:
    result = classifier.classify("Beliebiger Text.")
    assert "Platzhalter" in result.reasoning
    assert "kein LLM" in result.reasoning


def test_possible_parties_and_topic_are_empty_placeholder_stubs() -> None:
    """Namens-/Themenerkennung ist bewusst nicht Teil des Platzhalters."""
    result = classifier.classify("Text mit Namen wie Max Mustermann GmbH.")
    assert result.possible_parties == []
    assert result.topic is None
