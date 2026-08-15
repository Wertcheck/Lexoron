"""ProcessingError – verfolgt fehlgeschlagene, potenziell wiederholbare
Pipeline-Schritte (Prompt 31).

Schließt eine bislang offene Lücke: einzelne Pipeline-Stufen (OCR, Intake)
markierten einen Fehlschlag bereits als Endzustand (z. B.
`Document.ocr_status = "failed"`), aber es gab KEINEN Weg, es erneut zu
versuchen, außer den gesamten Datensatz manuell zu löschen und neu
anzulegen. Dieses Modell macht Fehlschläge sichtbar, nachvollziehbar und
gezielt wiederholbar - ohne einen externen Task-Queue-Dienst (Celery o. Ä.),
konsistent mit der bewusst einfachen, Ein-Prozess-Architektur des Projekts.

WICHTIG (Lehre aus dem Security Review, Prompt 27): `error_message` darf
NIEMALS den Inhalt eines Dokuments/einer Nachricht enthalten - nur die
technische Fehlermeldung der fehlgeschlagenen Operation (z. B. "Tesseract
nicht gefunden"). Aufrufer sind dafür verantwortlich, keine
Mandanteninhalte in die Exception-Message einzubetten - siehe
app/errors/service.py für die Stellen, die dieses Modell befüllen.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# "transient": vermutlich vorübergehend (Netzwerk, externe Abhängigkeit
# kurzzeitig nicht erreichbar) - wird automatisch mit Backoff wiederholt.
# "permanent": vermutlich dauerhaft (z. B. nicht unterstütztes
# Dateiformat, ungültige Eingabe) - wird NICHT automatisch wiederholt,
# braucht menschliche Prüfung.
VALID_ERROR_CATEGORIES = ("transient", "permanent")

# "pending_retry": wartet auf den nächsten automatischen Versuch.
# "retrying": ein Versuch läuft gerade (Parallelitätsschutz - verhindert,
# dass derselbe Fehlereintrag durch einen Doppelklick oder ein
# gleichzeitig laufendes Retry-Skript zweimal parallel bearbeitet wird).
# "failed_permanent": maximale Versuche erreicht ODER als dauerhaft
# eingestuft - braucht manuelle Aktion (Retry-Button oder Korrektur).
# "resolved": ein nachfolgender Versuch war erfolgreich.
VALID_PROCESSING_ERROR_STATUSES = (
    "pending_retry",
    "retrying",
    "failed_permanent",
    "resolved",
)


class ProcessingError(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "processing_errors"

    # Kein FK auf ein bestimmtes Modell (Document/Message/Matter je nach
    # Operation) - bewusst generisch wie bei AuditEvent, um EINE
    # Retry-Infrastruktur für mehrere Pipeline-Stufen zu teilen.
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # z. B. "ocr", "intake", "classification", "matter_matching" -
    # identifiziert, WELCHE Operation erneut ausgeführt werden muss.
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    error_category: Mapped[str] = mapped_column(String(16), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="pending_retry", nullable=False
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
