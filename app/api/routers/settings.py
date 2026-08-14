"""Einstellungen-Endpunkt (Prompt 21).

KRITISCH: `Settings` enthaelt `SecretStr`-Felder (`mail_password`,
`anthropic_api_key`). Dieser Router referenziert diese Felder an keiner
Stelle - `SettingsOut` wird explizit Feld fuer Feld aus dem
`Settings`-Objekt zusammengebaut (siehe app/api/schemas.py). Dadurch kann
ein zukuenftig ergaenztes Secret-Feld nicht versehentlich ueber diesen
Endpunkt exponiert werden, selbst wenn `SettingsOut` vergessen wuerde zu
aktualisieren - ein neues Feld erscheint schlicht nicht in der Antwort,
bis es hier bewusst ergaenzt wird.

Abgesichert per Test (`tests/test_api.py`): der Response-Body enthaelt
nachweislich weder den Wert von `mail_password` noch von
`anthropic_api_key`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.schemas import SettingsOut
from app.config import Settings, get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _database_url_kind(database_url: str) -> str:
    """Reduziert den vollen Connection-String auf die Datenbankart.

    Ein voller `database_url`-String kann bei PostgreSQL Zugangsdaten
    enthalten (postgresql://user:pass@host/db) - deshalb wird hier
    bewusst nie der volle String durchgereicht, nur die Art.
    """
    if database_url.startswith("sqlite"):
        return "sqlite"
    if database_url.startswith("postgresql"):
        return "postgresql"
    return "other"


@router.get("", response_model=SettingsOut)
def get_current_settings(settings: Settings = Depends(get_settings)) -> SettingsOut:
    return SettingsOut(
        app_env=settings.app_env,
        database_url_kind=_database_url_kind(settings.database_url),
        mail_provider=settings.mail_provider,
        mail_host=settings.mail_host,
        mail_mailbox=settings.mail_mailbox,
        mail_use_ssl=settings.mail_use_ssl,
        classification_low_confidence_threshold=(
            settings.classification_low_confidence_threshold
        ),
        matching_auto_assign_threshold=settings.matching_auto_assign_threshold,
        matching_review_threshold=settings.matching_review_threshold,
        research_min_score_for_sufficient=settings.research_min_score_for_sufficient,
        embedding_model_name=settings.embedding_model_name,
        ocr_enabled=settings.ocr_enabled,
        ocr_engine=settings.ocr_engine,
        ocr_languages=settings.ocr_languages,
        llm_provider=settings.llm_provider,
        claude_model_name=settings.claude_model_name,
        claude_max_tokens=settings.claude_max_tokens,
        require_human_approval_before_send=settings.require_human_approval_before_send,
        retention_days=settings.retention_days,
    )
