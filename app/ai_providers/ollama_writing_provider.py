"""OllamaWritingProvider – lokale Implementierung von `ClaudeWritingProvider`
über die lokale Ollama-HTTP-API (Local-First-Architektur, siehe
ARCHITECTURE.md §60).

DSGVO-/Datenschutz-Garantie wie bei `AnthropicClaudeWritingProvider`: diese
Klasse bekommt AUSSCHLIESSLICH eine bereits durch
`app/privacy/gateway.py: ClaudePrivacyGateway` pseudonymisierte und
Security-Check-geprüfte `ClaudeRequestPayload` - der Gateway sitzt bei
JEDEM Provider (lokal oder Cloud) davor, siehe app/web/service_factory.py.
Bei `AI_MODE=LOCAL_ONLY` (Standard) verlässt die Anfrage zusätzlich gar
nicht erst die Maschine - `base_url` zeigt standardmäßig auf
`http://localhost:11434`.
"""

from __future__ import annotations

import httpx

from app.ai_providers.claude_writing_provider import (
    WRITING_SYSTEM_PROMPT,
    ClaudeWritingResult,
    build_writing_prompt,
)
from app.privacy.gateway_schema import ClaudeRequestPayload


class OllamaUnavailableError(Exception):
    """Wird ausgelöst, wenn der lokale Ollama-Dienst beim tatsächlichen
    Aufruf nicht erreichbar ist oder einen Fehler liefert (z. B. Ollama
    nicht gestartet, falsches Modell). Getrennt von
    `ProviderNotConfiguredError` (app/ai_providers/factory.py) - jener
    Fehler betrifft die Konfiguration zur Bauzeit, dieser hier einen
    Laufzeit-/Erreichbarkeitsfehler beim tatsächlichen Aufruf."""


class OllamaWritingProvider:
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

    def write(self, payload: ClaudeRequestPayload) -> ClaudeWritingResult:
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": WRITING_SYSTEM_PROMPT},
                        {"role": "user", "content": build_writing_prompt(payload)},
                    ],
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

        text = data.get("message", {}).get("content", "")
        input_tokens = data.get("prompt_eval_count")
        output_tokens = data.get("eval_count")
        token_count = (
            input_tokens + output_tokens
            if input_tokens is not None and output_tokens is not None
            else None
        )

        return ClaudeWritingResult(
            text=text,
            token_count=token_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
