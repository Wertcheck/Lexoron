"""ModelProvider-Abstraktion (Prompt 34).

Schließt eine seit Prompt 03 offene Lücke: `settings.llm_provider`
existierte bereits als Konfigurationsfeld ("anthropic"), wurde aber nie
tatsächlich zur Provider-AUSWAHL genutzt - `app/web/service_factory.py`
baute `AnthropicClaudeWritingProvider`/`AnthropicClaudeReviewProvider`
fest verdrahtet, unabhängig vom Einstellungswert. `llm_provider` war
faktisch nur ein Anzeigefeld (siehe app/api/routers/settings.py).

Dieses Modul ist die EINZIGE Stelle im Projekt, die `settings.llm_provider`
tatsächlich auswertet und daraus eine konkrete Provider-Instanz baut -
`DraftingService`/`ReviewEngine` kennen nur die Protokolle
(`ClaudeWritingProvider`/`ClaudeReviewProvider`, siehe
app/ai_providers/claude_writing_provider.py bzw. app/review/provider.py),
nie eine konkrete Implementierung. Ein künftiger zweiter Provider (z. B.
ein lokales Modell über Ollama - siehe TODO.md, weiterhin eine offene
Entscheidung, HIER bewusst NICHT vorweggenommen/implementiert) würde
ausschließlich hier ergänzt werden müssen, ohne DraftingService,
ReviewEngine oder die Dashboard-Router anzufassen.

WICHTIG, ehrlich benannt: aktuell gibt es nur EINEN unterstützten Provider
("anthropic", validiert in app/config/settings.py). Diese Abstraktion
nimmt bewusst KEINE zweite, unfertige Implementierung vorweg - sie
schafft nur die saubere Erweiterungsstelle (Konzept "smallest sensible
step", konsistent mit dem restlichen Projekt).
"""

from __future__ import annotations

from app.ai_providers.anthropic_writing_provider import AnthropicClaudeWritingProvider
from app.ai_providers.claude_writing_provider import ClaudeWritingProvider
from app.config import Settings
from app.review.anthropic_review_provider import AnthropicClaudeReviewProvider
from app.review.provider import ClaudeReviewProvider


class ProviderNotConfiguredError(Exception):
    """Wird ausgelöst, wenn der konfigurierte Provider (aktuell immer
    "anthropic") keine gültigen Zugangsdaten hat - z. B. fehlender
    `ANTHROPIC_API_KEY`. Bewusst EINE gemeinsame Exception für Writing UND
    Review (statt zwei praktisch identischer Typen) - der Dashboard-Router
    fängt sie ab, um dem Anwalt eine verständliche Meldung statt eines
    Stacktrace zu zeigen (siehe app/web/drafts_router.py)."""


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
    """Baut den konfigurierten Schreib-Provider. Wirft `ValueError` bei
    einem unbekannten `llm_provider`-Wert - sollte praktisch nie
    auftreten, da `Settings` das Feld bereits beim Einlesen validiert
    (siehe app/config/settings.py: `llm_provider_must_be_supported`),
    aber als zweite Verteidigungslinie hier trotzdem geprüft, falls
    `Settings` künftig direkt (ohne Validierung) konstruiert würde."""
    if settings.llm_provider == "anthropic":
        api_key = _require_anthropic_api_key(settings)
        return AnthropicClaudeWritingProvider(
            api_key=api_key,
            model=settings.claude_model_name,
            max_tokens=settings.claude_max_tokens,
        )
    raise ValueError(f"Unbekannter llm_provider: {settings.llm_provider!r}")


def build_review_provider(settings: Settings) -> ClaudeReviewProvider:
    """Wie `build_writing_provider`, für die Review-Engine."""
    if settings.llm_provider == "anthropic":
        api_key = _require_anthropic_api_key(settings)
        return AnthropicClaudeReviewProvider(
            api_key=api_key,
            model=settings.claude_model_name,
            max_tokens=settings.claude_max_tokens,
        )
    raise ValueError(f"Unbekannter llm_provider: {settings.llm_provider!r}")
