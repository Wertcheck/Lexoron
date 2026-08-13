"""KnowledgeItem – freigegebenes Kanzleiwissen.

Wichtig (Konzept §5 / Prompt 12/13): Inhalte duerfen erst nach expliziter
Freigabe (`approval_status == "approved"`) in Entwuerfe einfliessen. Eine
einmalige Aenderung des Anwalts an einem Entwurf wird NICHT automatisch zu
Kanzleiwissen - dieser Uebernahmeschritt ist bewusst ein eigener,
spaeterer Workflow (Prompt 13) und nicht Teil dieses Datenmodells.
"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_items"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    practice_area: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # pending / approved / deactivated - Default bewusst restriktiv:
    # ungeprueftes Wissen darf nicht automatisch verwendet werden.
    approval_status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )
