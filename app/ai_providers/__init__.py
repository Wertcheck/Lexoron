"""KI-Provider-Abstraktionen (Architekturvorgabe, Schritt 4 von 5).

Zwei Protocols, wie von der Vorgabe (Punkt 11) gefordert:

- `LocalAIProvider`: lokale KI-Aufgaben (Dokumentenverständnis, Aktenkontext,
  Wissensabruf, Fristen). Aktuelle konkrete Implementierung
  (`RuleBasedLocalAIProvider`) bündelt die bereits bestehenden, getesteten
  Platzhalter-Services (Prompt 08-12) zu EINER austauschbaren Schnittstelle
  - keine Neuimplementierung der Logik. Eine zukünftige lokale
  Provider-Implementierung könnte dasselbe Protocol erfüllen, ohne den
  Workflow zu ändern.
- `ClaudeWritingProvider`: externe sprachliche Textproduktion. NOCH OHNE
  konkrete Implementierung - der tatsächliche Claude-API-Aufruf ist
  bewusst ein separater, letzter Schritt (verschmilzt mit Prompt 17), der
  erst nach ausdrücklicher Freigabe gebaut wird.

`DraftGenerationOrchestrator` verbindet beide Abstraktionen mit dem
Privacy Gateway (Schritt 1-3) zu einem vollständigen, aber weiterhin ohne
echten Claude-Aufruf lauffähigen Ablauf - demonstriert die Kernanforderung
"Der Workflow darf nicht direkt von Claude abhängig sein" (Vorgabe Punkt 11).
"""

from app.ai_providers.anthropic_writing_provider import AnthropicClaudeWritingProvider
from app.ai_providers.claude_writing_provider import ClaudeWritingProvider, ClaudeWritingResult
from app.ai_providers.local_ai_provider import (
    DraftPreparationResult,
    LocalAIProvider,
    RuleBasedLocalAIProvider,
)
from app.ai_providers.orchestrator import DraftGenerationOrchestrator, DraftGenerationResult

__all__ = [
    "LocalAIProvider",
    "RuleBasedLocalAIProvider",
    "DraftPreparationResult",
    "ClaudeWritingProvider",
    "ClaudeWritingResult",
    "AnthropicClaudeWritingProvider",
    "DraftGenerationOrchestrator",
    "DraftGenerationResult",
]
