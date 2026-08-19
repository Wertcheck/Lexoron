"""Draft – Antwortentwurf.

Versionierung ist hier zentral: JEDE neue Version ist eine EIGENE Zeile,
verkettet über `previous_version_id` - eine bestehende Draft-Zeile wird
NIE überschrieben (weder Inhalt noch Version), egal ob die neue Version
durch KI-Neugenerierung (`app/drafting/service.py`, ggf. angestoßen durch
eine `AttorneyInstruction`) oder durch manuelle Bearbeitung entsteht
(`app/feedback/service.py` bei "approved_with_edits", oder eine
zukünftige eigenständige Bearbeitungsaktion im Dashboard). Die zentrale,
einzige Stelle, die tatsächlich neue Draft-Zeilen anlegt, ist
`app/drafting/versioning.py: create_new_draft_version` - siehe dort für
die Begründung dieser Zentralisierung.

`version` bleibt eine fortlaufende Ganzzahl innerhalb einer Versionskette
(1, 2, 3, ...) - `previous_version_id` ist die eigentliche, verlässliche
Verkettung; `version` ist die für Menschen lesbare Nummer entlang dieser
Kette. `status` bildet den Freigabeweg ab, ersetzt aber nicht die
vollständige Workflow-State-Machine aus Prompt 20/ARCHITECTURE.md §6.

WICHTIG zur Historie: eine ÄLTERE Version wird nach dem Entstehen einer
neueren NICHT nachträglich verändert (auch ihr `status` bleibt
eingefroren) - nur die jeweils aktuelle/neueste Zeile einer Kette erhält
Status-Updates ohne Versionssprung (z. B. eine reine Freigabe ohne
inhaltliche Änderung, siehe DraftFeedbackService).
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Draft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drafts"

    matter_id: Mapped[str] = mapped_column(
        ForeignKey("matters.id"), nullable=False, index=True
    )
    message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # draft / legal_review / approved / rejected - siehe Hinweis oben.
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    # Self-FK: bildet die Versionskette. None = allererste Version (v1)
    # einer Entwurfslinie. Siehe Moduldocstring.
    previous_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("drafts.id"), nullable=True, index=True
    )

    matter: Mapped["Matter"] = relationship(back_populates="drafts")
    previous_version: Mapped["Draft | None"] = relationship(
        remote_side="Draft.id", foreign_keys=[previous_version_id]
    )
    quality_ratings: Mapped[list["DraftQualityRating"]] = relationship(
        back_populates="draft", cascade="all, delete-orphan"
    )
