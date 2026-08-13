"""Tests fuer app/deadlines/extractor.py (Prompt 10).

Nutzt ausschliesslich synthetische Testtexte."""

from datetime import date

from app.deadlines.extractor import PlaceholderDeadlineExtractor

extractor = PlaceholderDeadlineExtractor()


def test_extracts_numeric_date_with_deadline_keyword() -> None:
    results = extractor.extract("Bitte antworten Sie bis zum 15.03.2027.")
    assert len(results) == 1
    assert results[0].due_date == date(2027, 3, 15)
    assert results[0].confidence >= 0.4


def test_bare_date_without_keyword_gets_low_confidence() -> None:
    results = extractor.extract("Wir beziehen uns auf unser Schreiben vom 15.03.2027.")
    assert len(results) == 1
    assert results[0].due_date == date(2027, 3, 15)
    assert results[0].confidence <= 0.2


def test_extracts_date_with_german_month_name() -> None:
    results = extractor.extract("Frist bis spätestens 15. März 2027.")
    assert len(results) == 1
    assert results[0].due_date == date(2027, 3, 15)


def test_extracts_relative_period_without_due_date() -> None:
    results = extractor.extract("Bitte antworten Sie binnen zwei Wochen.")
    assert len(results) == 1
    assert results[0].due_date is None
    assert "zwei" in results[0].raw_date_text.lower()


def test_no_dates_returns_empty_list() -> None:
    results = extractor.extract("Ein Text ganz ohne Datumsangaben.")
    assert results == []


def test_multiple_dates_are_all_extracted() -> None:
    text = "Erste Frist: bis zum 01.01.2027. Zweite Frist: bis zum 15.06.2027."
    results = extractor.extract(text)
    assert len(results) == 2
    due_dates = {r.due_date for r in results}
    assert due_dates == {date(2027, 1, 1), date(2027, 6, 15)}


def test_confidence_never_signals_high_certainty() -> None:
    """Auch mit Schluesselwort bleibt die Konfidenz eines Platzhalters
    deutlich unter "sicher"."""
    results = extractor.extract("Frist: spätestens bis zum 01.01.2027.")
    assert all(r.confidence <= 0.6 for r in results)


def test_invalid_date_is_not_extracted() -> None:
    """z. B. 32.13.2027 ist kein gueltiges Datum - darf nicht als Frist
    durchrutschen."""
    results = extractor.extract("Ungültiges Datum: 32.13.2027.")
    assert results == []


def test_reasoning_mentions_placeholder_nature() -> None:
    results = extractor.extract("Bis zum 15.03.2027 antworten.")
    assert "Platzhalter" in results[0].reasoning
    assert "kein LLM" in results[0].reasoning
