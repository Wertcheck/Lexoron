"""Embedding – gespeicherter Vektor für semantische Suche.

Generisch gehalten (entity_type/entity_id) analog zu `AuditEvent`, damit
sowohl `Document` als auch `KnowledgeItem` (und später ggf. `Source`)
indiziert werden können, ohne separate Tabellen pro Entität zu brauchen.

Der Vektor wird als JSON-Array (Text) gespeichert statt als BLOB - das
hält die Implementierung fuer den Prototyp einfach und portabel (SQLite
hat keinen nativen Vektortyp). Bei wachsendem Datenvolumen kann dies durch
einen dedizierten Vektorspeicher ersetzt werden, ohne die Such-API
(app/search/service.py) zu aendern.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Embedding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "embeddings"

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    # JSON-serialisiertes list[float].
    vector_json: Mapped[str] = mapped_column(Text, nullable=False)
