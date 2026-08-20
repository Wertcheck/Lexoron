"""Lokale Keyword-Heuristik zur Vorkategorisierung von Pilot-Feedback
(Schritt 3).

Bewusst KEIN Claude-API-Aufruf - siehe Moduldocstring in
app/models/pilot_feedback.py für die Begründung (ARCHITECTURE.md §27:
Claude ausschließlich für sprachliche Textproduktion bereits lokal
bestimmten Inhalts, niemals für Analyse/Klassifikation von potenziell noch
ungeprüftem Nutzertext). Struktur/Konfidenz-Deckelung analog zu
app/classification/classifier.py (Prompt 08,
`PlaceholderDocumentClassifier`) - eine reine Regex-/Keyword-Heuristik ist
KEIN Ersatz für menschliche Prüfung, daher hart gedeckelte, absichtlich
niedrige Konfidenz."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.pilot_feedback import VALID_FEEDBACK_CATEGORIES

#: Hart gedeckelte Obergrenze - dieselbe Begründung wie bei
#: PlaceholderDocumentClassifier: eine Keyword-Heuristik darf nie als
#: "hinreichend sicher" erscheinen.
_MAX_CONFIDENCE = 0.4

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fehler": (
        "fehler",
        "bug",
        "absturz",
        "funktioniert nicht",
        "geht nicht",
        "kaputt",
        "fehlermeldung",
        "exception",
    ),
    "verbesserungsvorschlag": (
        "wäre schön",
        "vorschlag",
        "verbesserung",
        "feature",
        "wünsche mir",
        "sollte",
        "könnte man",
    ),
    "frage": ("wie kann ich", "frage", "wie funktioniert", "?"),
    "lob": ("super", "klasse", "toll", "danke", "gut gemacht", "hilfreich"),
}

#: Hinweise darauf, dass ein Vorschlag tatsächlich das Verhalten der KI
#: selbst (Prompts/Systemregeln) betrifft, statt nur eine Oberflächen-
#: Kleinigkeit - löst die Admin-Freigabe-Schleife aus (siehe
#: app/pilot_feedback/service.py). Bewusst eine ENGERE, eigene Liste statt
#: einer Ableitung aus "verbesserungsvorschlag" - nicht jeder
#: Verbesserungsvorschlag betrifft das KI-Verhalten (z. B. reine
#: UI-Wünsche).
_SYSTEM_CHANGE_KEYWORDS: tuple[str, ...] = (
    "prompt",
    "system",
    "die ki soll",
    "die ki sollte",
    "anweisung ändern",
    "verhalten anpassen",
    "systemregel",
    "formulierung anpassen",
)


@dataclass(frozen=True)
class FeedbackClassification:
    suggested_category: str
    confidence: float
    suggests_system_change: bool


def classify_feedback(message: str) -> FeedbackClassification:
    """Ordnet einen Feedback-Text einer Kategorie zu und markiert, ob er
    auf eine System-/Prompt-Änderung hindeutet. Liefert IMMER ein Ergebnis
    (Fallback "sonstiges", Konfidenz 0.0) statt eine Ausnahme - eine
    fehlgeschlagene Vorkategorisierung darf die Feedback-Abgabe selbst nie
    verhindern."""
    text = (message or "").strip().lower()
    if not text:
        return FeedbackClassification(
            suggested_category="sonstiges", confidence=0.0, suggests_system_change=False
        )

    best_category = "sonstiges"
    best_hits = 0
    for category, keywords in _CATEGORY_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in text)
        if hits > best_hits:
            best_hits = hits
            best_category = category

    assert best_category in VALID_FEEDBACK_CATEGORIES | {"sonstiges"}

    confidence = min(_MAX_CONFIDENCE, 0.15 * best_hits) if best_hits else 0.0
    suggests_system_change = any(keyword in text for keyword in _SYSTEM_CHANGE_KEYWORDS)

    return FeedbackClassification(
        suggested_category=best_category,
        confidence=confidence,
        suggests_system_change=suggests_system_change,
    )
