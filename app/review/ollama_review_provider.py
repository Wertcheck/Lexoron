"""OllamaReviewProvider – lokale Implementierung von `ClaudeReviewProvider`
über die lokale Ollama-HTTP-API (Local-First-Architektur, siehe
ARCHITECTURE.md §60).

Wie bei `OllamaWritingProvider`: strukturell kein Zugriff auf
Mandantendaten-Modelle, ausschließlich die bereits pseudonymisierte
`ClaudeRequestPayload`. `format: "json"` weist Ollama an, ausschließlich
valides JSON zurückzugeben (analog zur Erwartung an Claude im Systemprompt,
aber hier zusätzlich strukturell erzwungen). JSON-Parsing-Fehler werden wie
beim Anthropic-Pendant NICHT verschluckt, sondern als `ValueError`
weitergegeben."""

from __future__ import annotations

import json

import httpx

from app.ai_providers.ollama_writing_provider import OllamaUnavailableError
from app.privacy.gateway_schema import ClaudeRequestPayload
from app.review.provider import REVIEW_SYSTEM_PROMPT, build_review_prompt
from app.review.schema import ReviewResult


class OllamaReviewProvider:
    def __init__(self, *, base_url: str, model: str, timeout_seconds: float = 120.0) -> None:
        if not base_url or not base_url.strip():
            raise ValueError(
                "base_url darf nicht leer sein - OLLAMA_BASE_URL in .env setzen"
            )
        if not model or not model.strip():
            raise ValueError(
                "model darf nicht leer sein - OLLAMA_MODEL_NAME in .env setzen"
            )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def review(self, payload: ClaudeRequestPayload) -> ReviewResult:
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                        {"role": "user", "content": build_review_prompt(payload)},
                    ],
                    "format": "json",
                    "stream": False,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(
                f"Lokaler Ollama-Dienst ({self.base_url}) nicht erreichbar: {exc}"
            ) from exc

        text = data.get("message", {}).get("content", "").strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("Review-Engine: Antwort war kein valides JSON") from exc

        input_tokens = data.get("prompt_eval_count")
        output_tokens = data.get("eval_count")

        return ReviewResult(**parsed, input_tokens=input_tokens, output_tokens=output_tokens)
