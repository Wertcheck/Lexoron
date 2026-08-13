"""Dokumentklassifikation (Prompt 08).

Erkennt Dokumenttyp, mögliches Aktenzeichen, mögliche Beteiligte, Thema und
Handlungsbedarf als strukturierte, strikt validierte Daten. Unsicherheit
wird immer als Score + Begründung mitgeliefert - niemals stillschweigend
verworfen.

WICHTIG (Stand dieses Prompts): Es kommt bewusst noch KEIN LLM zum
Einsatz. `PlaceholderDocumentClassifier` ist eine einfache, regelbasierte
Heuristik mit absichtlich niedriger Konfidenz - sie dient nur dazu, das
Schema, die Datenbankanbindung und die "niedrige Konfidenz -> keine
automatische Aktenzuordnung"-Logik zu testen. Die echte LLM-basierte
Klassifikation (Claude-API oder ggf. ein lokales Modell, siehe
ARCHITECTURE.md-Diskussion) entsteht erst mit der Modell-Anbindung
(Prompt 17/34) und ersetzt diesen Platzhalter, ohne das Schema oder die
Datenbankstruktur zu ändern (siehe `DocumentClassifier`-Protocol).
"""

from app.classification.classifier import DocumentClassifier, PlaceholderDocumentClassifier
from app.classification.schema import ClassificationResult
from app.classification.service import ClassificationService

__all__ = [
    "DocumentClassifier",
    "PlaceholderDocumentClassifier",
    "ClassificationResult",
    "ClassificationService",
]
