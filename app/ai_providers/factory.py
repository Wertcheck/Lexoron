"""ModelProvider-Abstraktion (Prompt 34; Local-First-Architektur 20.08.,
siehe ARCHITECTURE.md §60).

Dieses Modul ist die EINZIGE Stelle im Projekt, die `settings.ai_mode`
tatsächlich auswertet und daraus eine konkrete Provider-Instanz baut -
`DraftingService`/`ReviewEngine` kennen nur die Protokolle
(`ClaudeWritingProvider`/`ClaudeReviewProvider`, siehe
app/ai_providers/claude_writing_provider.py bzw. app/review/provider.py),
nie eine konkrete Implementierung.

- `ai_mode="LOCAL_ONLY"` (Standard): `OllamaWritingProvider`/
  `OllamaReviewProvider` (app/ai_providers/ollama_writing_provider.py,
  app/review/ollama_review_provider.py) - ausschließlich der lokale
  Ollama-Dienst, keine Anfrage verlässt die Maschine.
- `ai_mode="HYBRID"`: `AnthropicClaudeWritingProvider`/
  `AnthropicClaudeReviewProvider` - der Text hat den lokalen
  Privacy-Gateway (Pseudonymisierung + Security-Check) bereits VOR dieser
  Stelle durchlaufen (siehe app/web/service_factory.py), unabhängig davon,
  welcher Provider hier gebaut wird.
"""

from __future__ import annotations

from app.ai_providers.anthropic_writing_provider import AnthropicClaudeWritingProvider
from app.ai_providers.claude_writing_provider import ClaudeWritingProvider
from app.ai_providers.ollama_writing_provider import OllamaWritingProvider
from app.config import Settings
from app.review.anthropic_review_provider import AnthropicClaudeReviewProvider
from app.review.ollama_review_provider import OllamaReviewProvider
from app.review.provider import ClaudeReviewProvider


class ProviderNotConfiguredError(Exception):
    """Wird ausgelöst, wenn der konfigurierte Provider keine gültigen
    Zugangsdaten/Konfiguration hat - z. B. fehlender `ANTHROPIC_API_KEY`
    bei `ai_mode="HYBRID"`. Bewusst EINE gemeinsame Exception für Writing
    UND Review (statt zwei praktisch identischer Typen) - der
    Dashboard-Router fängt sie ab, um dem Anwalt eine verständliche
    Meldung statt eines Stacktrace zu zeigen (siehe app/web/drafts_router.py).

    Betrifft nur Konfigurationsfehler zur Bauzeit - eine Erreichbarkeits-
    Störung des lokalen Ollama-Diensts zur LAUFZEIT eines Aufrufs wird
    stattdessen als `OllamaUnavailableError` gemeldet (siehe
    app/ai_providers/ollama_writing_provider.py)."""


def _require_anthropic_api_key(settings: Settings) -> str:
    api_key = (
        settings.anthropic_api_key.get_secret_value()
        if settings.anthropic_api_key is not None
        else None
    )
    if not api_key or not api_key.strip():
        raise ProviderNotConfiguredError(
            "ANTHROPIC_API_KEY ist nicht konfiguriert - in der .env-Datei hinterlegen "
            "(nötig für AI_MODE=HYBRID)."
        )
    return api_key


def build_writing_provider(settings: Settings) -> ClaudeWritingProvider:
    """Baut den konfigurierten Schreib-Provider anhand von
    `settings.ai_mode`. Wirft `ValueError` bei einem unbekannten
    `ai_mode`-Wert - sollte praktisch nie auftreten, da `Settings` das
    Feld bereits beim Einlesen validiert (siehe app/config/settings.py:
    `ai_mode_must_be_supported`), aber als zweite Verteidigungslinie hier
    trotzdem geprüft, falls `Settings` künftig direkt (ohne Validierung)
    konstruiert würde."""
    if settings.ai_mode == "HYBRID":
        api_key = _require_anthropic_api_key(settings)
        return AnthropicClaudeWritingProvider(
            api_key=api_key,
            model=settings.claude_model_name,
            max_tokens=settings.claude_max_tokens,
        )
    if settings.ai_mode == "LOCAL_ONLY":
        return OllamaWritingProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model_name,
        )
    raise ValueError(f"Unbekannter ai_mode: {settings.ai_mode!r}")


def build_review_provider(settings: Settings) -> ClaudeReviewProvider:
    """Wie `build_writing_provider`, für die Review-Engine."""
    if settings.ai_mode == "HYBRID":
        api_key = _require_anthropic_api_key(settings)
        return AnthropicClaudeReviewProvider(
            api_key=api_key,
            model=settings.claude_model_name,
            max_tokens=settings.claude_max_tokens,
        )
    if settings.ai_mode == "LOCAL_ONLY":
        return OllamaReviewProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model_name,
        )
    raise ValueError(f"Unbekannter ai_mode: {settings.ai_mode!r}")
