"""DraftGenerationOrchestrator – verbindet alle Abstraktionen zum
vollständigen Ablauf aus der Architekturvorgabe:

LOCAL DATA -> Local AI (`LocalAIProvider`) -> Draft Preparation
  -> Privacy Gateway (`ClaudePrivacyGateway`, Schritt 1-3)
  -> ClaudeWritingProvider (Schritt 4, Protocol)
  -> lokale Rückführung (`ClaudePrivacyGateway.reconstruct_response`)

WICHTIG: Diese Klasse hängt ausschließlich von den drei Protocols/
Abstraktionen ab (`LocalAIProvider`, `ClaudePrivacyGateway`,
`ClaudeWritingProvider`) - sie importiert und kennt kein konkretes
Claude-SDK, keinen API-Key, keine HTTP-Bibliothek. Das ist die technische
Umsetzung von Vorgabe-Punkt 11 ("Der Workflow darf nicht direkt von
Claude abhängig sein").
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.ai_providers.claude_writing_provider import ClaudeWritingProvider
from app.ai_providers.local_ai_provider import LocalAIProvider
from app.privacy.gateway import ClaudePrivacyGateway


@dataclass
class DraftGenerationResult:
    success: bool
    text: str | None = None
    blocked_reasons: list[str] = field(default_factory=list)


class DraftGenerationOrchestrator:
    def __init__(
        self,
        local_ai: LocalAIProvider,
        gateway: ClaudePrivacyGateway,
        writing_provider: ClaudeWritingProvider,
    ) -> None:
        self.local_ai = local_ai
        self.gateway = gateway
        self.writing_provider = writing_provider

    def generate_draft_text(
        self,
        matter_id: str,
        purpose: str,
        db: Session,
        *,
        stil: str | None = None,
        vorlage: str | None = None,
    ) -> DraftGenerationResult:
        preparation = self.local_ai.prepare_draft_context(matter_id, db)

        gateway_result = self.gateway.prepare_request(
            purpose=purpose,
            sachverhalt=preparation.sachverhalt,
            argumentationspunkte=preparation.argumentationspunkte,
            quellenverweise=preparation.quellenverweise,
            stil=stil,
            vorlage=vorlage,
            known_entities=preparation.known_entities,
        )

        if not gateway_result.allowed:
            return DraftGenerationResult(
                success=False, text=None, blocked_reasons=gateway_result.reasons
            )

        pseudonymized_response = self.writing_provider.write(gateway_result.payload)
        reconstructed_text = self.gateway.reconstruct_response(
            pseudonymized_response, gateway_result.mappings
        )

        return DraftGenerationResult(success=True, text=reconstructed_text)
