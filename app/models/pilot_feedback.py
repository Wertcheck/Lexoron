"""PilotFeedback – Pilot-Feedback & Support (Schritt 3, 20.08.).

Getrennt vom bestehenden `DraftFeedback` (Prompt 13, anwaltliches Feedback
zu EINEM konkreten Entwurf) - dieses Modell erfasst allgemeines
Nutzer-Feedback zur Software selbst (Fehlerhinweis, Verbesserungsvorschlag,
Frage) über das Formular unter "Pilot-Feedback & Support".

`system_context_json` speichert AUSSCHLIESSLICH einen anonymisierten
Schnappschuss aus bereits vorhandenen, inhaltsfreien Ja/Nein-/Zaehlwerten
(app_env, Anzahl offener Fehler, Konfigurationsstatus - identisches Muster
zu app/web/monitoring_router.py) - NIEMALS vollständige Tracebacks,
Dateipfade oder Mandantendaten (siehe app/pilot_feedback/service.py:
_build_system_context).

`ai_suggested_category`/`ai_confidence` stammen aus einer LOKALEN
Keyword-Heuristik (app/pilot_feedback/classifier.py), bewusst KEIN
Claude-API-Aufruf - konsistent mit ARCHITECTURE.md §27 (Claude
ausschließlich für sprachliche Textproduktion bereits lokal bestimmten
Inhalts, niemals für Analyse/Klassifikation) und dem etablierten Muster aus
Prompt 08 (PlaceholderDocumentClassifier).

`requires_admin_review`/`review_status` bilden die vom Anwalt geforderte
Freigabe-Schleife für Vorschläge, die auf eine System-/Prompt-Änderung
hindeuten: ein Feedback-Eintrag wird NIE automatisch umgesetzt - er landet
lediglich als "zur Freigabe" markiert in der Admin-Übersicht
(app/web/feedback_router.py), die eigentliche Umsetzung bleibt manuelle
Entwicklungsarbeit (CLAUDE.md: "keine autonome KI-Entscheidung",
"Architektur wird nicht eigenmächtig verändert")."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

VALID_FEEDBACK_CATEGORIES = frozenset(
    {"fehler", "verbesserungsvorschlag", "frage", "lob", "sonstiges"}
)
VALID_REVIEW_STATUSES = frozenset({"neu", "zur_pruefung", "freigegeben", "abgelehnt"})


class PilotFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pilot_feedback"

    # Freitext wie bei DraftFeedback.actor (z. B. E-Mail) statt strikter FK
    # auf User - konsistent mit dem etablierten Projektmuster.
    submitted_by_actor: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    system_context_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    ai_suggested_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    requires_admin_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="neu")
    reviewed_by_actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
