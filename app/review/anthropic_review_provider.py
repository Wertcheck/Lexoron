"""AnthropicClaudeReviewProvider – konkrete Implementierung von
`ClaudeReviewProvider`, über das offizielle Anthropic-SDK.

Wie bei `AnthropicClaudeWritingProvider`: strukturell kein Zugriff auf
Mandantendaten-Modelle, ausschließlich die bereits pseudonymisierte
`ClaudeRequestPayload`.

JSON-Parsing-Fehler (Claude antwortet nicht im geforderten Format) werden
NICHT verschluckt - sie werden als `ValueError` weitergegeben, damit
`ReviewEngine` sie wie jeden anderen Fehler behandelt (protokollieren,
kontrolliert abbrechen, niemals stillschweigend ein leeres/falsches
Ergebnis vortäuschen).
"""

from __future__ import annotations

import json

import anthropic

from app.privacy.gateway_schema import ClaudeRequestPayload
from app.review.provider import REVIEW_SYSTEM_PROMPT, build_review_prompt
from app.review.schema import ReviewResult


class AnthropicClaudeReviewProvider:
    def __init__(self, *, api_key: str, model: str, max_tokens: int = 2000) -> None:
        if not api_key or not api_key.strip():
            raise ValueError(
                "api_key darf nicht leer sein - ANTHROPIC_API_KEY in .env setzen"
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def review(self, payload: ClaudeRequestPayload) -> ReviewResult:
        prompt_text = build_review_prompt(payload)

        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=REVIEW_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt_text}],
        )

        text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Review-Engine: Antwort war kein valides JSON"
            ) from exc

        input_tokens = None
        output_tokens = None
        if response.usage is not None:
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

        return ReviewResult(**parsed, input_tokens=input_tokens, output_tokens=output_tokens)
