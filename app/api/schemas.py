"""Pydantic-Response-Schemas fuer das FastAPI-Backend (Prompt 21).

Bewusst als ALLOWLIST formuliert: jedes Schema listet explizit die
Felder, die nach aussen gehen - kein SQLAlchemy-Modell wird direkt
serialisiert. Das verhindert, dass ein spaeter am Modell ergaenztes,
sensibles Feld (z. B. ein interner Hash oder ein zukuenftiges Secret)
automatisch ueber die API sichtbar wuerde - dasselbe Prinzip wie beim
Privacy-Gateway-Payload (Schritt 3 der Privacy-Architektur), hier auf die
Backend-API angewendet.

WICHTIG (Konzept Prompt 21, woertlich): "Noch keine Produktions-
authentifizierung vortaeuschen." Es gibt in diesem gesamten Modul keine
Authentifizierungs-/Autorisierungspruefung - jeder mit Zugriff auf den
laufenden Server kann alle Endpunkte aufrufen. Das ist fuer den aktuellen
Entwicklungsstand explizit so vorgesehen (echte Rollen/Berechtigungen
folgen erst in Prompt 26) und darf nicht als bereits produktionsreif
missverstanden werden.

Ausserdem bewusst nur LESENDE (GET) Endpunkte in diesem gesamten Modul -
Mutationen (Freigabe/Ablehnung eines Entwurfs etc.) bleiben den
bestehenden Service-Methoden vorbehalten, bis eine echte Zugriffskontrolle
existiert.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class _ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Inbox (Message) ---


class MessageOut(_ORMBase):
    id: str
    matter_id: str | None
    external_message_id: str | None
    direction: str
    sender: str | None
    recipient: str | None
    subject: str | None
    body_text: str | None
    created_at: datetime
    updated_at: datetime


# --- Akten (Matter) ---


class MatterOut(_ORMBase):
    id: str
    client_id: str
    reference_number: str | None
    title: str
    practice_area: str | None
    status: str
    created_at: datetime
    updated_at: datetime


# --- Dokumente (Document) ---


class DocumentOut(_ORMBase):
    id: str
    matter_id: str | None
    message_id: str | None
    original_filename: str | None
    mime_type: str | None
    content_hash: str | None
    ocr_status: str
    classified_type: str | None
    classification_confidence: float | None
    classification_topic: str | None
    classification_action_required: bool | None
    created_at: datetime
    updated_at: datetime
    # Bewusst NICHT enthalten: file_path (interner Ablagepfad), extracted_text
    # (kann grosse Mengen an Mandanteninhalt enthalten - je nach Bedarf ueber
    # einen spaeteren, gezielten Detail-Endpunkt statt der Listenansicht).


# --- Entwuerfe (Draft) ---


class DraftOut(_ORMBase):
    id: str
    matter_id: str
    message_id: str | None
    content: str
    version: int
    status: str
    created_by_user_id: str | None
    created_at: datetime
    updated_at: datetime


# --- Quellen (Source) ---


class SourceOut(_ORMBase):
    id: str
    title: str
    source_type: str
    reference: str | None
    url: str | None
    document_date: date | None
    valid_from: date | None
    valid_until: date | None
    approval_level: str
    provider_name: str | None
    created_at: datetime
    updated_at: datetime


# --- Kanzlei-Wissen (KnowledgeItem) ---


class KnowledgeItemOut(_ORMBase):
    id: str
    title: str
    content: str
    category: str | None
    practice_area: str | None
    version: int
    approval_status: str
    source: str | None
    valid_from: date | None
    valid_until: date | None
    created_at: datetime
    updated_at: datetime


# --- Aufgaben (Task, Deadline) ---


class TaskOut(_ORMBase):
    id: str
    matter_id: str
    title: str
    description: str | None
    due_date: date | None
    status: str
    created_at: datetime
    updated_at: datetime


class DeadlineOut(_ORMBase):
    id: str
    matter_id: str
    document_id: str | None
    source_text: str | None
    due_date: date | None
    confidence: float | None
    review_status: str
    created_at: datetime
    updated_at: datetime


# --- Einstellungen (Settings) ---


class SettingsOut(BaseModel):
    """Bewusst KEIN `from_attributes`/ORM-Bezug: wird explizit im Router aus
    einzelnen, garantiert sekretfreien Feldern zusammengebaut (siehe
    routers/settings.py), statt ein Settings-Objekt mit SecretStr-Feldern
    ueberhaupt in die Naehe der Serialisierung zu bringen.
    """

    app_env: str
    database_url_kind: str  # nur "sqlite" oder "postgresql", nie der volle String
    mail_provider: str | None
    mail_host: str | None
    mail_mailbox: str
    mail_use_ssl: bool
    classification_low_confidence_threshold: float
    matching_auto_assign_threshold: float
    matching_review_threshold: float
    research_min_score_for_sufficient: float
    embedding_model_name: str
    ocr_enabled: bool
    ocr_engine: str
    ocr_languages: str
    ai_mode: str
    claude_model_name: str
    claude_max_tokens: int
    require_human_approval_before_send: bool
    retention_days: int
    # Bewusst NICHT enthalten: mail_password, anthropic_api_key (SecretStr),
    # tesseract_cmd/intake_watched_folders/intake_storage_dir/mail_username
    # (koennen interne Pfad-/Netzwerkdetails preisgeben, ohne Mehrwert fuer
    # das Dashboard).

    @classmethod
    def from_settings(cls, settings: "Settings") -> "SettingsOut":  # noqa: F821
        """Einzige Konstruktionsstelle dieser Allowlist - genutzt vom
        Settings-API-Endpunkt (app/api/routers/settings.py) UND vom
        Backup-Snapshot (app/backup/service.py, Schritt 3), damit beide
        garantiert dieselben (sekretfreien) Felder liefern."""
        db_url = settings.database_url
        if db_url.startswith("sqlite"):
            database_url_kind = "sqlite"
        elif db_url.startswith("postgresql"):
            database_url_kind = "postgresql"
        else:
            database_url_kind = "other"

        return cls(
            app_env=settings.app_env,
            database_url_kind=database_url_kind,
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
            ai_mode=settings.ai_mode,
            claude_model_name=settings.claude_model_name,
            claude_max_tokens=settings.claude_max_tokens,
            require_human_approval_before_send=settings.require_human_approval_before_send,
            retention_days=settings.retention_days,
        )


# --- Audit ---


class AuditEventOut(_ORMBase):
    id: str
    entity_type: str
    entity_id: str
    event_type: str
    actor: str
    details: str | None
    created_at: datetime
