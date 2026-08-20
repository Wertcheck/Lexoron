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
    build_writing_prompt_cache_blocks,
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
        # Prompt-Caching (Schritt 3): das Systemprompt ist projektweit für
        # JEDEN Aufruf identisch (siehe WRITING_SYSTEM_PROMPT) - als
        # gecachter Block markiert, spart es ab dem zweiten Aufruf
        # innerhalb des Cache-Fensters Eingabe-Tokens. Der Nachrichtentext
        # trennt zusätzlich den wiederkehrenden Aktenkontext vom variablen
        # Schreibauftrag (siehe build_writing_prompt_cache_blocks).
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[
                {
                    "type": "text",
                    "text": WRITING_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": build_writing_prompt_cache_blocks(payload)}],
        )

        text = "".join(
            block.text for block in response.content if block.type == "text"
        )

        token_count = None
        input_tokens = None
        output_tokens = None
        if response.usage is not None:
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            token_count = input_tokens + output_tokens

        return ClaudeWritingResult(
            text=text,
            token_count=token_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
