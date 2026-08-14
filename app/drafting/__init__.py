"""Drafting-Service (Prompt 17).

Eingaben (Konzept, wörtlich): aktueller Vorgang, relevante Akteninhalte,
freigegebenes Kanzleiwissen, zugelassene Rechtsquellen und Kanzleivorlage.
Ausgabe: Entwurf, Quellenliste, offene Prüfungen, Unsicherheiten und
verwendete Wissenselemente.

`DraftingService` baut auf bereits bestehenden, getesteten Bausteinen auf
(bewusst keine Neuimplementierung der zugrundeliegenden Logik):
- `RuleBasedLocalAIProvider` (Prompt 16/Privacy-Schritt 4) für Sachverhalt/
  Argumentationspunkte/bekannte Entitäten.
- `LegalResearchService` (Prompt 15) für zugelassene, mit vollständigem
  Beleg versehene Rechtsquellen.
- `DocumentSearchService.search_knowledge_base` (Prompt 11/12) für
  freigegebenes Kanzleiwissen, mit Entity-ID-Tracking (nicht nur
  Text-Schnipsel wie beim einfacheren `LocalAIProvider`-Pfad).
- `ClaudePrivacyGateway` + `ClaudeWritingProvider` + `ApiCallLogger`
  (Privacy-Schritte 1-5) für die eigentliche, DSGVO-konforme Textproduktion.

Der Service selbst hat KEINE Versand-Fähigkeit - es gibt in diesem Modul
keine Methode, die eine E-Mail verschickt oder einen Versand auslöst.
"""

from app.drafting.schema import DraftingResult, KnowledgeItemReference, SourceReference
from app.drafting.service import DraftingService

__all__ = [
    "DraftingService",
    "DraftingResult",
    "SourceReference",
    "KnowledgeItemReference",
]
