"""KnowledgeItem – freigegebenes Kanzleiwissen.

Wichtig (Konzept §5 / Prompt 12/13): Inhalte duerfen erst nach expliziter
Freigabe (`approval_status == "approved"`) in Entwuerfe einfliessen. Eine
einmalige Aenderung des Anwalts an einem Entwurf wird NICHT automatisch zu
Kanzleiwissen - dieser Uebernahmeschritt ist bewusst ein eigener,
spaeterer Workflow (Prompt 13) und nicht Teil dieses Datenmodells.

Erweiterung Prompt 12: `source` (Herkunft, z. B. "Anwalt XY" oder Verweis
auf einen frueheren Entwurf) und `valid_from`/`valid_until`
(Gueltigkeitsbereich) ergaenzen die in Prompt 04 angelegten Basisfelder.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
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
    # Herkunft des Wissens, z. B. "Anwalt XY" oder ein Verweis auf den
    # Ursprung (frueherer Entwurf, externe Vorlage etc.) - frei formuliert,
    # da die genaue Herkunftskette je nach Quelle variiert.
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Gueltigkeitsbereich (Zeitraum) - z. B. relevant bei Textbausteinen zu
    # befristeten Regelungen. None = zeitlich unbegrenzt gueltig.
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
