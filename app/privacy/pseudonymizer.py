"""Pseudonymizer – ersetzt erkannte PII durch Platzhalter wie [MANDANT_01].

WICHTIG: `PseudonymMapping`-Objekte werden von dieser Klasse nur im
Rückgabewert übergeben - es findet HIER keine Persistierung statt. Ob und
wie die Zuordnung lokal gespeichert wird (für die Rückführung nach einem
späteren Claude-API-Aufruf), entscheidet der Aufrufer bzw. der noch zu
bauende `ClaudePrivacyGateway`. Diese Klasse selbst sendet niemals etwas
irgendwohin - reine, seiteneffektfreie Textverarbeitung.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.privacy.detectors import detect_all

_PLACEHOLDER_PREFIX_BY_CATEGORY = {
    "mandant": "MANDANT",
    "gegner": "GEGNER",
    "anwalt": "ANWALT",
    "gericht": "GERICHT",
    "aktenzeichen": "AKTENZEICHEN",
    "adresse": "ADRESSE",
    "datum": "DATUM",
    "betrag": "BETRAG",
    "vertrag": "VERTRAG",
    "email": "EMAIL",
    "telefon": "TELEFON",
    "iban": "IBAN",
    "steuer_id": "STEUER_ID",
    "kundennummer": "KUNDENNUMMER",
}


@dataclass
class PseudonymMapping:
    placeholder: str
    category: str
    original_value: str


class Pseudonymizer:
    def pseudonymize(
        self, text: str, *, known_entities: dict[str, list[str]] | None = None
    ) -> tuple[str, list[PseudonymMapping]]:
        """Ersetzt alle erkannten PII-Vorkommen durch Platzhalter.

        Derselbe Originalwert erhält innerhalb EINES Aufrufs immer
        denselben Platzhalter (z. B. "Max Mustermann" wird überall zu
        [MANDANT_01], nicht bei jedem Vorkommen neu nummeriert).
        """
        spans = detect_all(text, known_entities)

        value_to_placeholder: dict[tuple[str, str], str] = {}
        counters: dict[str, int] = {}
        mappings: list[PseudonymMapping] = []

        for span in spans:
            key = (span.category, span.value.lower())
            if key not in value_to_placeholder:
                counters[span.category] = counters.get(span.category, 0) + 1
                prefix = _PLACEHOLDER_PREFIX_BY_CATEGORY.get(
                    span.category, span.category.upper()
                )
                placeholder = f"[{prefix}_{counters[span.category]:02d}]"
                value_to_placeholder[key] = placeholder
                mappings.append(
                    PseudonymMapping(
                        placeholder=placeholder,
                        category=span.category,
                        original_value=span.value,
                    )
                )

        # Von hinten nach vorne ersetzen, damit sich Indizes vorheriger
        # (frueherer) Treffer durch die Ersetzung nicht verschieben.
        result = text
        for span in sorted(spans, key=lambda s: s.start, reverse=True):
            placeholder = value_to_placeholder[(span.category, span.value.lower())]
            result = result[: span.start] + placeholder + result[span.end :]

        return result, mappings

    def reconstruct(self, text: str, mappings: list[PseudonymMapping]) -> str:
        """Ersetzt Platzhalter wieder durch die Originalwerte - rein
        lokal, nachdem eine (pseudonymisierte) Antwort zurückgekommen ist."""
        result = text
        for mapping in mappings:
            result = result.replace(mapping.placeholder, mapping.original_value)
        return result
