"""DocumentClassifier – Protocol + Platzhalter-Implementierung.

`DocumentClassifier` ist absichtlich als Protocol gehalten (wie
`MailProvider` in app/mail/base.py), damit eine spätere LLM-basierte
Implementierung (Prompt 17/34) diese Abstraktion einfach ersetzen kann,
ohne `ClassificationService` oder das Schema zu ändern.

`PlaceholderDocumentClassifier` nutzt reine Keyword-/Regex-Heuristiken -
KEIN LLM, KEIN maschinelles Lernen. Die Konfidenz ist absichtlich niedrig
gedeckelt, damit dieser Platzhalter niemals fälschlich als "sicher genug für
automatische Aktenzuordnung" gilt.
"""

from __future__ import annotations

import re
from typing import Protocol

from app.classification.schema import ClassificationResult

# Absichtlich niedrig: ein regelbasierter Platzhalter soll nie als
# hochsicher gelten, selbst wenn mehrere Keywords treffen.
_PLACEHOLDER_MAX_CONFIDENCE = 0.4

_DOCUMENT_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Rechnung": ("rechnung", "invoice", "rechnungsnummer"),
    "Vollmacht": ("vollmacht",),
    "Kündigungsschreiben": ("kündig", "kuendig"),
    "Mahnung": ("mahnung", "zahlungserinnerung"),
    "Klage/Schriftsatz": ("klage", "klageschrift", "schriftsatz"),
    "Gerichtliches Schreiben": ("gericht", "amtsgericht", "landgericht", "aktenzeichen des gerichts"),
    "Vertrag": ("vertrag", "vereinbarung"),
}

_ACTION_REQUIRED_KEYWORDS = (
    "frist",
    "dringend",
    "bis zum",
    "innerhalb von",
    "spätestens",
    "spaetestens",
)

# Grobe Muster fuer ein Aktenzeichen (z. B. "Az.: 123/24", "Aktenzeichen 45-2024").
_MATTER_REFERENCE_PATTERN = re.compile(
    r"(?:az\.?|aktenzeichen)\s*[:.]?\s*([A-Za-z0-9][A-Za-z0-9/\-]{2,20})",
    re.IGNORECASE,
)


class DocumentClassifier(Protocol):
    def classify(
        self, text: str, *, filename: str | None = None
    ) -> ClassificationResult: ...


class PlaceholderDocumentClassifier:
    """Regelbasierter Platzhalter ohne LLM/ML - siehe Moduldocstring."""

    def classify(
        self, text: str, *, filename: str | None = None
    ) -> ClassificationResult:
        normalized = text.lower()

        document_type, matched_keywords = self._detect_document_type(normalized)
        matter_reference = self._detect_matter_reference(text)
        action_required = any(kw in normalized for kw in _ACTION_REQUIRED_KEYWORDS)

        confidence = self._compute_confidence(matched_keywords)
        reasoning = self._build_reasoning(
            document_type, matched_keywords, matter_reference, action_required
        )

        return ClassificationResult(
            document_type=document_type,
            possible_matter_reference=matter_reference,
            possible_parties=[],  # Platzhalter: keine Namenserkennung ohne LLM
            topic=None,  # Platzhalter: keine Themenzusammenfassung ohne LLM
            action_required=action_required,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _detect_document_type(self, normalized_text: str) -> tuple[str, list[str]]:
        for document_type, keywords in _DOCUMENT_TYPE_KEYWORDS.items():
            matched = [kw for kw in keywords if kw in normalized_text]
            if matched:
                return document_type, matched
        return "Unbekannt", []

    def _detect_matter_reference(self, text: str) -> str | None:
        match = _MATTER_REFERENCE_PATTERN.search(text)
        return match.group(1) if match else None

    def _compute_confidence(self, matched_keywords: list[str]) -> float:
        if not matched_keywords:
            return 0.1
        # Mehr Treffer = etwas mehr (aber weiterhin niedrige) Konfidenz;
        # nie über _PLACEHOLDER_MAX_CONFIDENCE.
        return min(_PLACEHOLDER_MAX_CONFIDENCE, 0.2 + 0.1 * len(matched_keywords))

    def _build_reasoning(
        self,
        document_type: str,
        matched_keywords: list[str],
        matter_reference: str | None,
        action_required: bool,
    ) -> str:
        parts = [
            "Platzhalter-Klassifikation (regelbasiert, kein LLM).",
            f"Dokumenttyp '{document_type}' "
            + (
                f"aufgrund der Schlüsselwörter {matched_keywords} vermutet."
                if matched_keywords
                else "konnte nicht anhand bekannter Schlüsselwörter erkannt werden."
            ),
        ]
        if matter_reference:
            parts.append(f"Mögliches Aktenzeichen im Text gefunden: '{matter_reference}'.")
        if action_required:
            parts.append("Hinweise auf Handlungsbedarf/Frist im Text gefunden.")
        parts.append(
            "Konfidenz ist bewusst niedrig gehalten - dieses Ergebnis darf NICHT für "
            "automatische Aktenzuordnung verwendet werden."
        )
        return " ".join(parts)
