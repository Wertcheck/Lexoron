"""DraftFeedback – anwaltliches Feedback zu einem KI-Entwurf.

Wichtig (Konzept Prompt 13, wörtlich): "Übernehme Änderungen niemals
automatisch als globale Regel." Ein Feedback-Eintrag speichert nur, was
der Anwalt zu EINEM konkreten Entwurf gesagt/geändert hat - er wird NIE
automatisch zu Kanzleiwissen. Die Übernahme ist ein separater, expliziter
Workflow (`app/feedback/service.py: promote_to_knowledge`).

`approval_status` (bewusst kein DB-Enum, siehe Konvention in anderen
Modellen): "approved" / "approved_with_edits" / "rejected".
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DraftFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "draft_feedback"

    draft_id: Mapped[str] = mapped_column(
        ForeignKey("drafts.id"), nullable=False, index=True
    )
    # Schnappschuss des Entwurfsinhalts VOR dieser Feedback-Aktion - bleibt
    # unveraendert erhalten, auch wenn der Draft selbst danach aktualisiert
    # wird (siehe DraftFeedbackService).
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    # Nur gesetzt, wenn der Anwalt den Inhalt tatsaechlich veraendert hat.
    edited_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False)
    # Freitext wie bei AuditEvent.actor (z. B. E-Mail des Anwalts) - bewusst
    # keine strikte FK auf User, um Tests/fruehe Nutzung ohne angelegte
    # User-Datensaetze zu ermoeglichen.
    actor: Mapped[str] = mapped_column(String(128), nullable=False)

    draft: Mapped["Draft"] = relationship()
