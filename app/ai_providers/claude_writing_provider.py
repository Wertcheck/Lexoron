"""ClaudeWritingProvider – Protocol für externe sprachliche Textproduktion.

BEWUSST NOCH OHNE KONKRETE IMPLEMENTIERUNG. Der tatsächliche Claude-API-
Aufruf ist laut Entwicklungsplan ein separater, letzter Schritt
(verschmilzt mit Prompt 17), der erst nach ausdrücklicher Freigabe gebaut
wird - siehe ARCHITECTURE.md §27.

Das Protocol existiert bereits jetzt, damit der Workflow
(`DraftGenerationOrchestrator`) ausschließlich von dieser Abstraktion
abhängt, NIEMALS von einem konkreten SDK/einer konkreten Modell-Anbindung
(Architekturvorgabe Punkt 11, wörtlich: "Der Workflow darf nicht direkt
von Claude abhängig sein").

Nimmt bewusst NUR eine `ClaudeRequestPayload` entgegen (das
Allowlist-Schema aus Schritt 3) - es gibt keine Methode, die freien Text
oder beliebige Datenstrukturen an ein externes Modell schicken könnte.
"""

from __future__ import annotations

from typing import Protocol

from app.privacy.gateway_schema import ClaudeRequestPayload


class ClaudeWritingProvider(Protocol):
    def write(self, payload: ClaudeRequestPayload) -> str:
        """Sendet AUSSCHLIESSLICH die bereits pseudonymisierte,
        Allowlist-geprüfte Payload und gibt den (weiterhin
        pseudonymisierten) Antworttext zurück. Die lokale Rekonstruktion
        übernimmt der Aufrufer (siehe
        `ClaudePrivacyGateway.reconstruct_response`)."""
        ...
