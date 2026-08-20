"""PilotFeedbackService – Entgegennahme und Admin-Freigabe-Schleife für
Pilot-Feedback & Support (Schritt 3).

Zwei Kernoperationen:

1. `submit`: nimmt das Formular entgegen, hängt einen anonymisierten
   Systemkontext-Schnappschuss an (NUR bereits vorhandene Ja/Nein-/
   Zaehlwerte, siehe `_build_system_context` - niemals Tracebacks,
   Dateipfade oder Mandantendaten), lässt die lokale Keyword-Heuristik
   (app/pilot_feedback/classifier.py) eine Kategorie vorschlagen und
   markiert Einträge, die auf eine System-/Prompt-Änderung hindeuten,
   als `requires_admin_review=True`.
2. `review`: die vom Anwalt geforderte Freigabe-Schleife - ein Admin
   markiert einen Eintrag als "freigegeben" oder "abgelehnt". Setzt
   NIEMALS selbst eine System-/Prompt-Änderung um (siehe
   app/models/pilot_feedback.py-Docstring) - reine Status-/
   Nachvollziehbarkeits-Verwaltung, jede tatsächliche Umsetzung bleibt
   manuelle Entwicklungsarbeit.
"""

from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditEvent, PilotFeedback, ProcessingError
from app.pilot_feedback.classifier import classify_feedback
from app.pilot_feedback.schema import PilotFeedbackInput

_VALID_REVIEW_ACTIONS = frozenset({"freigegeben", "abgelehnt"})


def _build_system_context(db: Session) -> str:
    """Baut den anonymisierten Systemkontext-Schnappschuss - AUSSCHLIESSLICH
    bereits an anderer Stelle verifizierte, inhaltsfreie Werte (identisches
    Muster zu app/web/monitoring_router.py). Fällt bei jedem Fehler auf
    `None` zurück statt die Feedback-Abgabe selbst zu gefährden."""
    settings = get_settings()
    try:
        pending_errors = (
            db.query(func.count(ProcessingError.id))
            .filter(ProcessingError.status == "pending_retry")
            .scalar()
        )
    except Exception:  # noqa: BLE001 - Kontext ist optional, Abgabe darf nie scheitern
        pending_errors = None

    context = {
        "app_env": settings.app_env,
        "ocr_enabled": settings.ocr_enabled,
        "claude_api_configured": settings.anthropic_api_key is not None,
        "pending_processing_errors": pending_errors,
    }
    return json.dumps(context, ensure_ascii=False)


class PilotFeedbackService:
    def submit(
        self, db: Session, data: PilotFeedbackInput, *, actor: str
    ) -> PilotFeedback:
        classification = classify_feedback(data.message)

        entry = PilotFeedback(
            submitted_by_actor=actor,
            category=data.category,
            message=data.message,
            contact_email=data.contact_email,
            system_context_json=_build_system_context(db),
            ai_suggested_category=classification.suggested_category,
            ai_confidence=classification.confidence,
            requires_admin_review=classification.suggests_system_change,
            review_status=(
                "zur_pruefung" if classification.suggests_system_change else "neu"
            ),
        )
        db.add(entry)
        db.flush()

        db.add(
            AuditEvent(
                entity_type="PilotFeedback",
                entity_id=entry.id,
                event_type="pilot_feedback_submitted",
                actor=actor,
                details=f"Kategorie: {data.category}",
            )
        )
        db.commit()
        db.refresh(entry)
        return entry

    def list_pending_review(self, db: Session) -> list[PilotFeedback]:
        return (
            db.query(PilotFeedback)
            .filter(PilotFeedback.review_status == "zur_pruefung")
            .order_by(PilotFeedback.created_at.desc())
            .all()
        )

    def list_all(self, db: Session) -> list[PilotFeedback]:
        return db.query(PilotFeedback).order_by(PilotFeedback.created_at.desc()).all()

    def review(
        self,
        db: Session,
        feedback: PilotFeedback,
        *,
        action: str,
        actor: str,
        comment: str | None = None,
    ) -> PilotFeedback:
        if action not in _VALID_REVIEW_ACTIONS:
            raise ValueError(
                f"action muss einer von {sorted(_VALID_REVIEW_ACTIONS)} sein, war: {action!r}"
            )
        feedback.review_status = action
        feedback.reviewed_by_actor = actor
        feedback.review_comment = comment

        db.add(
            AuditEvent(
                entity_type="PilotFeedback",
                entity_id=feedback.id,
                event_type=f"pilot_feedback_{action}",
                actor=actor,
                details=comment,
            )
        )
        db.commit()
        db.refresh(feedback)
        return feedback
