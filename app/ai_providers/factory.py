"""ModelProvider-Abstraktion (Prompt 34; seit §63 ausschliesslich Claude/
Anthropic, siehe ARCHITECTURE.md §63 - vorher Local-First mit Ollama, §60;
seit §65 zusaetzlich `build_local_llm_provider` fuer den lokalen
PFLICHT-Zwischenschritt vor Claude, siehe ARCHITECTURE.md §65).

Dieses Modul bleibt die EINZIGE Stelle im Projekt, die eine konkrete
Provider-Instanz baut - `DraftingService`/`ReviewEngine` kennen nur die
Protokolle (`ClaudeWritingProvider`/`ClaudeReviewProvider`/
`LocalLLMProvider`, siehe app/ai_providers/claude_writing_provider.py,
app/review/provider.py bzw. app/ai_providers/local_llm_provider.py), nie
eine konkrete Implementierung. Fuer Claude gibt es keine lokale
Alternative - `build_writing_provider`/`build_review_provider` bauen immer
einen `AnthropicClaudeWritingProvider`/`AnthropicClaudeReviewProvider`;
fehlt der API-Key, wird das als Konfigurationsfehler gemeldet
(`ProviderNotConfiguredError`), nicht stillschweigend auf einen lokalen
Fallback umgeschaltet.
"""

from __future__ import annotations

from app.ai_providers.anthropic_writing_provider import AnthropicClaudeWritingProvider
from app.ai_providers.claude_writing_provider import ClaudeWritingProvider
from app.ai_providers.local_llm_provider import LocalLLMProvider
from app.ai_providers.ollama_provider import OllamaLocalLLMProvider
from app.config import Settings
from app.review.anthropic_review_provider import AnthropicClaudeReviewProvider
from app.review.provider import ClaudeReviewProvider


class ProviderNotConfiguredError(Exception):
    """Wird ausgelöst, wenn kein gültiger `ANTHROPIC_API_KEY` konfiguriert
    ist. Bewusst EINE gemeinsame Exception für Writing UND Review (statt
    zwei praktisch identischer Typen) - der Dashboard-Router fängt sie ab,
    um dem Anwalt eine verständliche Meldung statt eines Stacktrace zu
    zeigen (siehe app/web/drafts_router.py)."""


def _require_anthropic_api_key(settings: Settings) -> str:
    api_key = (
        settings.anthropic_api_key.get_secret_value()
        if settings.anthropic_api_key is not None
        else None
    )
    if not api_key or not api_key.strip():
        raise ProviderNotConfiguredError(
            "ANTHROPIC_API_KEY ist nicht konfiguriert - in der .env-Datei hinterlegen."
        )
    return api_key


def build_writing_provider(settings: Settings) -> ClaudeWritingProvider:
    """Baut den Anthropic-Schreib-Provider. Wirft `ProviderNotConfiguredError`,
    wenn kein `ANTHROPIC_API_KEY` hinterlegt ist."""
    api_key = _require_anthropic_api_key(settings)
    return AnthropicClaudeWritingProvider(
        api_key=api_key,
        model=settings.claude_model_name,
        max_tokens=settings.claude_max_tokens,
    )


def build_review_provider(settings: Settings) -> ClaudeReviewProvider:
    """Wie `build_writing_provider`, für die Review-Engine."""
    api_key = _require_anthropic_api_key(settings)
    return AnthropicClaudeReviewProvider(
        api_key=api_key,
        model=settings.claude_model_name,
        max_tokens=settings.claude_max_tokens,
    )


def build_local_llm_provider(settings: Settings) -> LocalLLMProvider | None:
    """Baut den lokalen KI-Provider (§65) - oder `None`, wenn
    `settings.local_ai_enabled=False` (Standard). `None` bedeutet fuer
    `DraftingService`: kein lokaler Zwischenschritt, unveraendertes
    Verhalten wie vor §65 - NICHT "lokale KI deaktiviert, aber trotzdem
    versuchen". Ist `local_ai_enabled=True`, wird IMMER ein Provider
    zurueckgegeben (aktuell ausschliesslich `local_ai_runtime="ollama"` -
    von `Settings.local_ai_runtime_must_be_supported` bereits validiert)."""
    if not settings.local_ai_enabled:
        return None
    return OllamaLocalLLMProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )
