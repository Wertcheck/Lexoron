"""service_factory – baut die "echten" Drafting-/Feedback-/AttorneyInstruction-
Services aus der zentralen Konfiguration, für die Dashboard-Routen
(app/web/drafts_router.py).

Bisher (vor Prompt 23) wurden diese Services ausschließlich in Tests
zusammengebaut - keine Anwendungsschicht hat sie tatsächlich für echte
Nutzung instanziiert. Diese Factory schließt die Lücke, DAMIT die neue
"Änderungen übernehmen & neu formulieren"-Aktion im Dashboard funktioniert.

Der teure Teil (Embedding-Modell) wird über `lru_cache` genau EINMAL pro
Prozess geladen, nicht bei jeder Anfrage neu.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai_providers.anthropic_writing_provider import AnthropicClaudeWritingProvider
from app.ai_providers.claude_writing_provider import ClaudeWritingProvider
from app.ai_providers.local_ai_provider import RuleBasedLocalAIProvider
from app.attorney_instructions.service import AttorneyInstructionService
from app.config import get_settings
from app.drafting.service import DraftingService
from app.feedback.service import DraftFeedbackService
from app.privacy.gateway import ClaudePrivacyGateway
from app.research.service import LegalResearchService
from app.review.anthropic_review_provider import AnthropicClaudeReviewProvider
from app.review.engine import ReviewEngine
from app.review.provider import ClaudeReviewProvider
from app.search.embeddings import FastEmbedProvider
from app.search.service import DocumentSearchService


class WritingProviderNotConfiguredError(Exception):
    """Wird ausgelöst, wenn keine Claude-API-Zugangsdaten hinterlegt sind.

    Bewusst eine EIGENE, klar erkennbare Exception statt der rohen
    `ValueError` aus `AnthropicClaudeWritingProvider.__init__` - der
    Dashboard-Router fängt genau diese ab, um dem Anwalt eine
    verständliche Meldung statt eines Stacktrace zu zeigen.
    """


@lru_cache(maxsize=1)
def get_document_search_service() -> DocumentSearchService:
    """Singleton pro Prozess - das Embedding-Modell wird beim ersten
    tatsächlichen `embed()`-Aufruf lazy geladen (siehe FastEmbedProvider),
    aber die Provider-Instanz selbst muss nicht wiederholt neu gebaut
    werden."""
    settings = get_settings()
    return DocumentSearchService(FastEmbedProvider(settings.embedding_model_name))


def get_drafting_service() -> DraftingService:
    """Baut einen funktionsfähigen `DraftingService` mit ECHTEM Claude-
    Writing-Provider. Wirft `WritingProviderNotConfiguredError`, wenn kein
    `ANTHROPIC_API_KEY` hinterlegt ist - der Router zeigt dann eine
    freundliche Meldung statt eines Serverfehlers."""
    settings = get_settings()
    search_service = get_document_search_service()
    research_service = LegalResearchService(
        search_service,
        min_score_for_sufficient=settings.research_min_score_for_sufficient,
    )

    writing_provider = _build_writing_provider(settings)

    return DraftingService(
        RuleBasedLocalAIProvider(search_service),
        research_service,
        search_service,
        ClaudePrivacyGateway(),
        writing_provider,
        model_name=settings.claude_model_name,
    )


def _build_writing_provider(settings) -> ClaudeWritingProvider:  # noqa: ANN001
    api_key = (
        settings.anthropic_api_key.get_secret_value()
        if settings.anthropic_api_key is not None
        else None
    )
    if not api_key or not api_key.strip():
        raise WritingProviderNotConfiguredError(
            "ANTHROPIC_API_KEY ist nicht konfiguriert - Entwurfs-"
            "(Neu-)Generierung ist erst nach Hinterlegen des Schlüssels "
            "in der .env-Datei möglich."
        )
    return AnthropicClaudeWritingProvider(
        api_key=api_key,
        model=settings.claude_model_name,
        max_tokens=settings.claude_max_tokens,
    )


def get_feedback_service() -> DraftFeedbackService:
    return DraftFeedbackService()


def get_review_engine() -> ReviewEngine:
    """Baut eine funktionsfähige `ReviewEngine` mit ECHTEM Claude-Review-
    Provider - wirft `WritingProviderNotConfiguredError` (derselbe Fehler-
    typ wie bei der Entwurfsproduktion, bewusst wiederverwendet statt
    einen zweiten, praktisch identischen Fehlertyp einzuführen), wenn kein
    `ANTHROPIC_API_KEY` hinterlegt ist."""
    settings = get_settings()
    search_service = get_document_search_service()
    research_service = LegalResearchService(
        search_service,
        min_score_for_sufficient=settings.research_min_score_for_sufficient,
    )
    review_provider = _build_review_provider(settings)

    return ReviewEngine(
        RuleBasedLocalAIProvider(search_service),
        research_service,
        ClaudePrivacyGateway(),
        review_provider,
        model_name=settings.claude_model_name,
    )


def _build_review_provider(settings) -> ClaudeReviewProvider:  # noqa: ANN001
    api_key = (
        settings.anthropic_api_key.get_secret_value()
        if settings.anthropic_api_key is not None
        else None
    )
    if not api_key or not api_key.strip():
        raise WritingProviderNotConfiguredError(
            "ANTHROPIC_API_KEY ist nicht konfiguriert - die Entwurfsprüfung "
            "(Review-Engine) ist erst nach Hinterlegen des Schlüssels in "
            "der .env-Datei möglich."
        )
    return AnthropicClaudeReviewProvider(
        api_key=api_key,
        model=settings.claude_model_name,
        max_tokens=settings.claude_max_tokens,
    )


def get_attorney_instruction_service() -> AttorneyInstructionService:
    """Für Aktionen, die tatsächlich eine Neugenerierung auslösen können
    (`apply_instruction`) - baut den vollen `DraftingService` inkl.
    Prüfung auf konfigurierten Claude-API-Key."""
    return AttorneyInstructionService(get_drafting_service())


def get_attorney_instruction_service_for_saving_only() -> AttorneyInstructionService:
    """Für die reine "Anmerkung speichern"-Aktion (`create_instruction`) -
    baut BEWUSST keinen `DraftingService` (kein Embedding-Modell, keine
    Claude-Konfigurationsprüfung). Speichern einer Anmerkung darf nicht
    daran scheitern, dass (noch) kein Claude-API-Key hinterlegt ist -
    das wird erst relevant, wenn tatsächlich neu generiert werden soll."""
    return AttorneyInstructionService(drafting_service=None)
