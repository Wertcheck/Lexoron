"""Tests für app/pilot_feedback/classifier.py (Schritt 3)."""

from __future__ import annotations

from app.pilot_feedback.classifier import classify_feedback


def test_bug_keywords_are_detected() -> None:
    result = classify_feedback("Die App stürzt beim Speichern ab, Fehlermeldung erscheint.")
    assert result.suggested_category == "fehler"


def test_feature_request_keywords_are_detected() -> None:
    result = classify_feedback("Vorschlag: könnte man einen Dark Mode ergänzen?")
    assert result.suggested_category == "verbesserungsvorschlag"


def test_praise_keywords_are_detected() -> None:
    result = classify_feedback("Super Arbeit, das ist wirklich hilfreich, danke!")
    assert result.suggested_category == "lob"


def test_empty_message_falls_back_to_sonstiges_with_zero_confidence() -> None:
    result = classify_feedback("   ")
    assert result.suggested_category == "sonstiges"
    assert result.confidence == 0.0


def test_confidence_is_hard_capped() -> None:
    """Analog zu PlaceholderDocumentClassifier (Prompt 08): eine reine
    Keyword-Heuristik darf niemals als 'hinreichend sicher' erscheinen."""
    text = "Fehler Bug Absturz funktioniert nicht geht nicht kaputt Fehlermeldung Exception"
    result = classify_feedback(text)
    assert result.confidence <= 0.4


def test_system_change_keywords_are_flagged() -> None:
    result = classify_feedback("Die KI soll die Formulierung anpassen, das Prompt ist zu streng.")
    assert result.suggests_system_change is True


def test_unrelated_feedback_does_not_flag_system_change() -> None:
    result = classify_feedback("Der Button ist etwas klein auf dem Handy.")
    assert result.suggests_system_change is False


def test_result_never_raises_on_arbitrary_text() -> None:
    weird_inputs = ["", "🎉🎉🎉", "a" * 5000, "SELECT * FROM users;"]
    for text in weird_inputs:
        result = classify_feedback(text)
        assert result.suggested_category in {
            "fehler",
            "verbesserungsvorschlag",
            "frage",
            "lob",
            "sonstiges",
        }
