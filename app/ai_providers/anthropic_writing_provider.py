"""AnthropicClaudeWritingProvider – erste konkrete Implementierung von
`ClaudeWritingProvider`, über das offizielle Anthropic-SDK.

DSGVO-/Datenschutz-Garantie (struktureller, nicht nur konventioneller
Schutz): Diese Klasse bekommt AUSSCHLIESSLICH eine `ClaudeRequestPayload`
(die sechs Allowlist-Felder, bereits pseudonymisiert und durch den
Security-Check aus Schritt 2 geprüft). Es gibt in dieser Datei keinen
Codepfad, der auf `Document`, `Matter`, `Message` oder andere
Mandantendaten-Modelle zugreifen könnte - der Datenfluss dorthin ist
bereits beim `ClaudePrivacyGateway` (Schritt 3) beendet.

Der API-Key wird ausschließlich zur Laufzeit aus der Konfiguration
gelesen (`SecretStr.get_secret_value()`), nie geloggt, nie im Klartext
gespeichert.
"""

from __future__ import annotations

import anthropic

from app.ai_providers.claude_writing_provider import (
    WRITING_SYSTEM_PROMPT,
    ClaudeWritingResult,
    build_writing_prompt,
)
from app.privacy.gateway_schema import ClaudeRequestPayload


class AnthropicClaudeWritingProvider:
    def __init__(self, *, api_key: str, model: str, max_tokens: int = 2000) -> None:
        if not api_key or not api_key.strip():
            raise ValueError(
                "api_key darf nicht leer sein - ANTHROPIC_API_KEY in .env setzen"
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def write(self, payload: ClaudeRequestPayload) -> ClaudeWritingResult:
        prompt_text = build_writing_prompt(payload)

        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=WRITING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt_text}],
        )

        text = "".join(
            block.text for block in response.content if block.type == "text"
        )

        token_count = None
        if response.usage is not None:
            token_count = (
                response.usage.input_tokens + response.usage.output_tokens
            )

        return ClaudeWritingResult(text=text, token_count=token_count)
