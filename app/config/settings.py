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

from pydantic import Field, SecretStr, field_validator, model_validator
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

    # --- E-Mail ---
    # "imap" ist der einzige aktuell implementierte Provider (Prompt 07,
    # siehe ARCHITECTURE.md §10 Entscheidung 4). Weitere Provider (z. B.
    # Microsoft Graph) koennen spaeter ueber dieselbe MailProvider-
    # Abstraktion ergaenzt werden, ohne den Workflow zu aendern.
    mail_provider: str | None = None
    mail_host: str | None = None
    mail_port: int = 993
    mail_username: str | None = None
    mail_password: SecretStr | None = None
    mail_mailbox: str = "INBOX"
    mail_use_ssl: bool = True
    # Ob abgerufene Nachrichten auf dem Server als gelesen markiert werden.
    # Sicherer Default True, damit ein wiederholter Abruf (z. B. nach einem
    # Neustart) nicht dieselben Nachrichten erneut als "neu" behandelt -
    # zusaetzlich schuetzt die externe Message-ID vor Duplikaten in der DB.
    mail_mark_seen: bool = True
    # Getrennter Ablagebereich für E-Mail-Anhänge (analog zu
    # intake_storage_dir für den Scan-Eingang, aber bewusst eigener
    # Ordner, um die Herkunft nachvollziehbar zu halten).
    mail_attachment_storage_dir: str = "data/mail_attachments"

    # --- Klassifikation ---
    # Ab welchem Konfidenzwert (0.0-1.0) eine Klassifikation als
    # ausreichend sicher gilt, um spaeter (Prompt 09) automatische
    # Aktenzuordnung zu erlauben. Unterhalb dieser Schwelle MUSS ein
    # Mensch pruefen - siehe Konzept Prompt 08/09.
    classification_low_confidence_threshold: float = 0.6

    # --- Aktenzuordnung (Matter-Matching) ---
    # Ab welchem Gesamt-Score (0.0-1.0) eine Akte automatisch zugeordnet
    # werden darf. Unterhalb liegt der Vorgang zur manuellen Pruefung vor.
    matching_auto_assign_threshold: float = 0.85
    # Unterhalb dieses Scores gilt: keine Akte gefunden (kein Vorschlag).
    matching_review_threshold: float = 0.4

    # --- Legal Research ---
    # Ab welchem Score ein einzelner Treffer als "ausreichend belegend"
    # gilt (siehe app/research/service.py).
    research_min_score_for_sufficient: float = 0.5

    # --- Suche / Embeddings (Prompt 11) ---
    # Lokales, mehrsprachiges Embedding-Modell (via "fastembed",
    # ONNX-Runtime - bewusst statt "sentence-transformers", das transitiv
    # volles PyTorch inkl. NVIDIA-CUDA mitinstalliert; siehe pyproject.toml)
    # fuer semantische Suche. Laeuft komplett offline nach einmaligem
    # Download, keine Mandantendaten verlassen dabei die Kanzlei-Umgebung.
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

    # --- OCR ---
    # Standardmaessig deaktiviert (sicherer Default) - muss bewusst
    # eingeschaltet werden. "tesseract" ist die einzige unterstuetzte
    # Engine (siehe ARCHITECTURE.md §10, Entscheidung 3, bestaetigt in
    # Prompt 06).
    ocr_enabled: bool = False
    ocr_engine: str = "tesseract"
    # Optionaler expliziter Pfad zur Tesseract-Programmdatei, z. B. unter
    # Windows "C:\\Program Files\\Tesseract-OCR\\tesseract.exe", falls
    # Tesseract nicht automatisch im PATH gefunden wird.
    tesseract_cmd: str | None = None
    # Sprachen fuer die Texterkennung (Tesseract-Sprachcodes,
    # "+"-getrennt), Default Deutsch + Englisch fuer Kanzleidokumente.
    ocr_languages: str = "deu+eng"
    # Ab welcher extrahierten Zeichenanzahl ein PDF als "hat bereits Text"
    # gilt statt als OCR-bedürftig (verhindert, dass einzelne Kopfzeilen-
    # Reste faelschlich als vollstaendiger Text gewertet werden).
    min_extracted_text_length: int = 20

    # --- LLM / Claude API (Platzhalter, echte Anbindung erst Prompt 17) ---
    llm_provider: str = "anthropic"
    anthropic_api_key: SecretStr | None = None
    # Nur der Modellname fuer Protokollierungs-/Konfigurationszwecke
    # (Schritt 5 der Privacy-Architektur) - keine echte API-Anbindung an
    # dieser Stelle, siehe app/ai_providers/claude_writing_provider.py.
    claude_model_name: str = "claude-sonnet-5"
    claude_max_tokens: int = 2000

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

    # --- Authentifizierung / Sessions (Prompt 26) ---
    # Signiert die Session-Cookies (itsdangerous). MUSS in Produktion aus
    # der Umgebung kommen - kein Default hier (siehe Validator unten), da
    # ein bekannter Fallback-Wert die gesamte Session-Signatur wertlos
    # machen würde. Im Entwicklungsbetrieb (app_env="development") wird
    # ein Prozess-lokaler Zufallswert verwendet, falls nicht gesetzt (siehe
    # get_settings) - bewusst NICHT persistent, damit ein fehlender Wert
    # in Produktion sofort auffällt (alle Sessions ungültig nach Neustart),
    # statt unbemerkt einen unsicheren Default zu verwenden.
    session_secret_key: SecretStr | None = None
    # 8 Stunden, wie vom Anwalt vorgegeben.
    session_max_age_seconds: int = 8 * 60 * 60
    # Cookie nur über HTTPS übertragen - sicherer Default für Produktion.
    # None = automatisch ableiten (siehe resolved_session_cookie_secure):
    # True außer in app_env="development" - lokale HTTP-Entwicklung und
    # die Testsuite (TestClient laeuft ueber "http://testserver", kein
    # TLS) brauchen sonst in JEDEM Test einen expliziten Override, nur um
    # ueberhaupt eine Session aufrechtzuerhalten. Ein expliziter Wert
    # (True/False in .env) hat immer Vorrang vor dieser Ableitung.
    session_cookie_secure: bool | None = None

    @property
    def resolved_session_cookie_secure(self) -> bool:
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return self.app_env != "development"

    @field_validator("session_max_age_seconds")
    @classmethod
    def session_max_age_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("session_max_age_seconds muss positiv sein")
        return value

    @property
    def resolved_session_secret_key(self) -> str:
        """Liefert den tatsächlich zu verwendenden Session-Schlüssel.

        In Produktion (`app_env != "development"`) MUSS `session_secret_key`
        gesetzt sein - ein fehlender Wert ist ein Konfigurationsfehler und
        führt bewusst zu einem harten Absturz beim Start, nicht zu einem
        stillen, unsicheren Fallback. Im Entwicklungsbetrieb wird ein
        zufälliger, NICHT persistenter Wert erzeugt (alle Sessions werden
        bei jedem Neustart ungültig) - praktikabel für lokale Entwicklung,
        ohne einen bekannten/erratbaren Default im Quellcode zu haben.
        """
        if self.session_secret_key is not None:
            return self.session_secret_key.get_secret_value()
        if self.app_env != "development":
            raise RuntimeError(
                "SESSION_SECRET_KEY ist nicht konfiguriert - in einer "
                "Nicht-Entwicklungsumgebung (APP_ENV != 'development') ist "
                "das ein hartes Konfigurationsfehler, kein Fallback erlaubt."
            )
        import secrets

        if not hasattr(self, "_dev_session_secret"):
            object.__setattr__(self, "_dev_session_secret", secrets.token_urlsafe(48))
        return self._dev_session_secret

    # --- Logging/Monitoring (Prompt 32) ---
    # Python-Standard-Log-Level-Namen ("DEBUG"/"INFO"/"WARNING"/"ERROR").
    log_level: str = "INFO"
    # None = nur Konsole (Standard, ausreichend für Entwicklung/Container-
    # Betrieb, wo stdout ohnehin gesammelt wird). Gesetzt = zusätzlich
    # eine rotierende lokale Log-Datei (sinnvoll für einen dauerhaft
    # laufenden Windows-Dienst ohne externe Log-Aggregation).
    log_file_path: str | None = None

    @field_validator("log_level")
    @classmethod
    def log_level_must_be_valid(cls, value: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in valid:
            raise ValueError(f"log_level muss einer von {sorted(valid)} sein, war: {value!r}")
        return upper

    # --- Vorlagen (Platzhalter, echte Logik erst Prompt 39) ---
    templates_dir: str = "data/templates"

    # --- Aufbewahrung / Loeschung (Platzhalter, echte Logik erst Prompt 35) ---
    # 0 = keine automatische Loeschung (sicherer Default).
    retention_days: int = 0

    @model_validator(mode="after")
    def review_threshold_must_not_exceed_auto_assign_threshold(self) -> "Settings":
        if self.matching_review_threshold > self.matching_auto_assign_threshold:
            raise ValueError(
                "matching_review_threshold darf matching_auto_assign_threshold "
                "nicht überschreiten"
            )
        return self

    @field_validator("retention_days")
    @classmethod
    def retention_days_must_not_be_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("retention_days darf nicht negativ sein")
        return value

    @field_validator(
        "matching_auto_assign_threshold",
        "matching_review_threshold",
        "research_min_score_for_sufficient",
    )
    @classmethod
    def matching_thresholds_must_be_a_fraction(cls, value: float) -> float:
        if not (0.0 <= value <= 1.0):
            raise ValueError("Schwellenwerte müssen zwischen 0.0 und 1.0 liegen")
        return value

    @field_validator("classification_low_confidence_threshold")
    @classmethod
    def classification_threshold_must_be_a_fraction(cls, value: float) -> float:
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                "classification_low_confidence_threshold muss zwischen 0.0 und 1.0 liegen"
            )
        return value

    @field_validator("min_extracted_text_length")
    @classmethod
    def min_extracted_text_length_must_not_be_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("min_extracted_text_length darf nicht negativ sein")
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
