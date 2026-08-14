"""Policy – versionierte Kanzleiregeln für den Prompt-/Policy-Layer (Prompt 16).

Bewusst ein eigenes, einfaches Modell statt Wiederverwendung von
`KnowledgeItem`: Policies sind KEIN zitierfähiges Fachwissen, sondern
Verhaltensregeln für die KI-gestützte Entwurfserstellung (z. B.
Schreibstil, Anrede-Konventionen) - konzeptionell etwas anderes.

Versionierung analog zum etablierten Muster (`Draft.version`,
`KnowledgeItem.version`): neue Version statt Überschreiben, nur eine
Version pro `name` ist gleichzeitig `is_active`.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Policy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "policies"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
