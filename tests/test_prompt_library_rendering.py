"""Tests für app/prompt_library/rendering.py (Schritt 3, Teil 2)."""

from __future__ import annotations

from app.prompt_library.rendering import extract_variables, render_template


def test_extract_variables_finds_all_placeholders_in_order() -> None:
    content = "Sehr geehrte/r {Mandant}, Ihre Frist läuft am {Frist} ab.\n{Dokumententext}"
    assert extract_variables(content) == ["Mandant", "Frist", "Dokumententext"]


def test_extract_variables_deduplicates() -> None:
    content = "{Mandant} ... {Mandant} ... {Frist}"
    assert extract_variables(content) == ["Mandant", "Frist"]


def test_extract_variables_empty_when_no_placeholders() -> None:
    assert extract_variables("Kein Platzhalter hier.") == []


def test_render_template_substitutes_known_variables() -> None:
    content = "Sehr geehrte/r {Mandant}, Frist: {Frist}."
    result = render_template(content, {"Mandant": "Max Mustermann", "Frist": "01.01.2027"})
    assert result == "Sehr geehrte/r Max Mustermann, Frist: 01.01.2027."


def test_render_template_leaves_unknown_variables_untouched() -> None:
    content = "{Mandant} - {UnbekanntesFeld}"
    result = render_template(content, {"Mandant": "Max Mustermann"})
    assert result == "Max Mustermann - {UnbekanntesFeld}"


def test_render_template_with_no_variables_provided() -> None:
    content = "Hallo {Mandant}"
    assert render_template(content, {}) == "Hallo {Mandant}"


def test_render_template_never_raises_on_malformed_braces() -> None:
    content = "Offene { Klammer ohne Namen"
    assert render_template(content, {"Mandant": "x"}) == content
