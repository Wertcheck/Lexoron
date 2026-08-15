"""DraftSourceLink / DraftKnowledgeItemLink – persistente Verknüpfung
zwischen einer konkreten Draft-VERSION und den Rechtsquellen/Kanzlei-
Wissenselementen, die TATSÄCHLICH für genau diese Version herangezogen
wurden (Prompt 24).

Vorher gab es dafür KEINE Persistenz: `DraftingResult.source_list`/
`knowledge_items_used` existierten nur transient im Rückgabewert von
`DraftingService.create_draft` (siehe app/drafting/schema.py) - im
Dashboard ließe sich sonst nur eine zum AKTUELLEN Zeitpunkt neu berechnete
Trefferliste zeigen, die von dem, was zur Erstellungszeit dieser Version
tatsächlich verwendet wurde, abweichen könnte (z. B. wenn eine Quelle
zwischenzeitlich als veraltet markiert wurde). Da das Projekt durchgängig
Wert auf Nachvollziehbarkeit legt ("niemals erfundene Fundstellen"), wird
hier die tatsächliche Verwendung zum Erstellungszeitpunkt festgehalten.

Jede neue Draft-Version (siehe app/drafting/versioning.py) bekommt ihre
EIGENEN Links - keine Wiederverwendung über Versionen hinweg, da sich die
verwendeten Quellen zwischen Versionen unterscheiden können.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DraftSourceLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "draft_source_links"

    draft_id: Mapped[str] = mapped_column(
        ForeignKey("drafts.id"), nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id"), nullable=False, index=True
    )

    source: Mapped["Source"] = relationship()


class DraftKnowledgeItemLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "draft_knowledge_item_links"

    draft_id: Mapped[str] = mapped_column(
        ForeignKey("drafts.id"), nullable=False, index=True
    )
    knowledge_item_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_items.id"), nullable=False, index=True
    )

    knowledge_item: Mapped["KnowledgeItem"] = relationship()
