"""Platzhalter-Substitution für Kanzlei-Prompts (Schritt 3, Teil 2).

Reine, seiteneffektfreie Textverarbeitung - kein Bezug zur Datenbank oder
zu Claude. Erkennt Platzhalter der Form `{Name}` (z. B. `{Mandant}`,
`{Frist}`, `{Dokumententext}`). Bewusst KEIN Fehler bei unbekannten
Variablen beim Rendern - ein unausgefülltes Feld bleibt einfach als
`{Name}` im Text stehen (sichtbar für den Nutzer, kein stiller
Informationsverlust, keine Ausnahme, die die Vorschau abbrechen würde)."""

from __future__ import annotations

import re

_VARIABLE_PATTERN = re.compile(r"\{([A-Za-zÄÖÜäöüß0-9_]+)\}")


def extract_variables(content: str) -> list[str]:
    """Liefert alle im Text vorkommenden Platzhalternamen, dedupliziert,
    in Vorkommensreihenfolge."""
    seen: list[str] = []
    for match in _VARIABLE_PATTERN.finditer(content):
        name = match.group(1)
        if name not in seen:
            seen.append(name)
    return seen


def render_template(content: str, variables: dict[str, str]) -> str:
    """Ersetzt bekannte Platzhalter durch ihre Werte. Unbekannte bleiben
    unverändert im Text stehen - `variables` kann bewusst eine Teilmenge
    der tatsächlich vorkommenden Platzhalter sein."""

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return variables.get(name, match.group(0))

    return _VARIABLE_PATTERN.sub(_replace, content)
