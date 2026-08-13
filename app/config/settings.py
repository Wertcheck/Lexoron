"""Zentrale Settings-Klasse.

Grundsaetze (siehe CLAUDE.md / ARCHITECTURE.md §7):
- Secrets kommen ausschliesslich aus Umgebungsvariablen/.env, niemals als
  Default-Wert im Code, und werden als SecretStr gehalten, damit sie nicht
  versehentlich in Logs oder Fehlermeldungen auftauchen.
- Sicherheitsrelevante Defaults sind bewusst restriktiv gewaehlt (z. B. kein
  automatischer Versand, keine automatische Loeschung).
- Bereiche mit noch offener fachlicher Logik (OCR, Mail, LLM, Rechtsquellen,
  Freigaberegeln, Vorlagen, Aufbewahrung) enthalten hier nur generische,
  minimale Platzhalterfelder. Die eigentliche Logik/Validierung entsteht in
  den jeweils zustaendigen spaeteren Prompts.
"""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Anwendung ---
    app_env: str = "development"

    # --- Datenbank ---
    # SQLite fuer den Prototyp. Bewusst als einfacher Connection-String
    # gehalten (SQLAlchemy-kompatibel), damit spaeter PostgreSQL nur ueber
    # diesen einen Wert eingesetzt werden kann, ohne Datenmodell oder
    # Geschaeftslogik zu aendern (siehe ARCHITECTURE.md §4/§10).
    database_url: str = "sqlite:///./data/kanzlei_ai.db"

    # --- Eingang / Intake ---
    # Liste ueberwachter Ordnerpfade. Leer = noch nichts konfiguriert.
    intake_watched_folders: list[str] = Field(default_factory=list)
    # Sicherer, konfigurierbarer Ablagebereich fuer sicher kopierte
    # Eingangsdateien (Prompt 05). Getrennt vom Original-Quellordner, damit
    # Bearbeitung nie direkt in einem vom Anwalt/Scanner beschriebenen
    # Ordner stattfindet.
    intake_storage_dir: str = "data/intake"

    # --- E-Mail (Platzhalter, echte Anbindung erst Prompt 07) ---
    mail_provider: str | None = None
    mail_username: str | None = None
    mail_password: SecretStr | None = None

    # --- OCR (Platzhalter, echte Logik erst Prompt 06) ---
    ocr_enabled: bool = False
    ocr_engine: str | None = None

    # --- LLM / Claude API (Platzhalter, echte Anbindung erst Prompt 17) ---
    llm_provider: str = "anthropic"
    anthropic_api_key: SecretStr | None = None

    # --- Rechtsquellen (Platzhalter, echte Logik erst Prompt 14/15) ---
    # Generische Liste erlaubter Quellen-Identifier; keine architektonische
    # Festlegung auf ein konkretes Schema an dieser Stelle.
    legal_sources_allowed: list[str] = Field(default_factory=list)

    # --- Freigaberegeln (Platzhalter, echte Logik erst Prompt 24/26) ---
    # Sicherer Default: Versand erfordert immer explizite menschliche
    # Freigabe. Dieser Wert steuert keinen automatischen Versand-Trigger -
    # ein solcher existiert im System bislang nicht (siehe Nicht-Ziele,
    # Konzept Abschnitt 1).
    require_human_approval_before_send: bool = True

    # --- Vorlagen (Platzhalter, echte Logik erst Prompt 39) ---
    templates_dir: str = "data/templates"

    # --- Aufbewahrung / Loeschung (Platzhalter, echte Logik erst Prompt 35) ---
    # 0 = keine automatische Loeschung (sicherer Default).
    retention_days: int = 0

    @field_validator("retention_days")
    @classmethod
    def retention_days_must_not_be_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("retention_days darf nicht negativ sein")
        return value

    @field_validator("intake_storage_dir")
    @classmethod
    def intake_storage_dir_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("intake_storage_dir darf nicht leer sein")
        return value

    @field_validator("intake_watched_folders", "legal_sources_allowed")
    @classmethod
    def no_blank_entries(cls, value: list[str]) -> list[str]:
        for entry in value:
            if not entry or not entry.strip():
                raise ValueError("Leere Einträge sind nicht zulässig")
        return value


@lru_cache
def get_settings() -> Settings:
    """Liefert eine gecachte Settings-Instanz.

    lru_cache sorgt dafuer, dass .env nur einmal pro Prozess gelesen wird.
    In Tests kann get_settings.cache_clear() genutzt werden, um mit
    veraenderten Umgebungsvariablen neu zu laden.
    """
    return Settings()
