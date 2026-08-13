"""WorkflowRun – ein Verarbeitungslauf (ein Vorgang durch die Pipeline).

`status` folgt den in ARCHITECTURE.md §6 festgelegten Zustaenden:
RECEIVED, PROCESSING, NEEDS_CLASSIFICATION, NEEDS_MATTER_MATCH,
READY_FOR_REVIEW, DRAFTED, LEGAL_REVIEW, APPROVED, ARCHIVED,
OUTBOX_READY, ERROR.

Die eigentliche State-Machine (erlaubte Uebergaenge, Validierung) entsteht
erst in Prompt 20 - hier wird bewusst nur der Status als freier, aber auf
diese bekannte Menge beschraenkter String abgelegt (leichtgewichtiger als
ein DB-Enum, einfacher migrierbar).
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

VALID_WORKFLOW_STATUSES = (
    "RECEIVED",
    "PROCESSING",
    "NEEDS_CLASSIFICATION",
    "NEEDS_MATTER_MATCH",
    "READY_FOR_REVIEW",
    "DRAFTED",
    "LEGAL_REVIEW",
    "APPROVED",
    "ARCHIVED",
    "OUTBOX_READY",
    "ERROR",
)


class WorkflowRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    matter_id: Mapped[str | None] = mapped_column(
        ForeignKey("matters.id"), nullable=True, index=True
    )
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="RECEIVED", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    matter: Mapped["Matter | None"] = relationship(back_populates="workflow_runs")
