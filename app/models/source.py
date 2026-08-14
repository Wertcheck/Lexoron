"""Source – Rechts-/Wissensquelle (Gesetz, Rechtsprechung, Verordnung ...).

Wichtig (Konzept §6): Rechtsquellen sind eine eigene Schicht, strikt
getrennt von Mandanten-/Aktendaten (keine `matter_id` hier). Jede Quelle
traegt die im Konzept geforderten Metadaten fuer Nachvollziehbarkeit und
Aktualitaet. Die KI darf keine Quelle erfinden - technisch durchgesetzt
dadurch, dass Quellen ausschliesslich ueber `SourceService.import_source`
(Prompt 14, manuelle Eingabe durch den Anwalt) entstehen, nie automatisch
generiert werden.

Erweiterung Prompt 14: `document_date` (Datum des Dokuments/der
Entscheidung selbst, z. B. Erlass-/Urteilsdatum - unterscheidet sich von
`valid_from`/`valid_until`, die den Geltungszeitraum beschreiben) und
`provider_name` (welcher `SourceProvider` diese Quelle geliefert/bestaetigt
hat, siehe app/sources/provider.py) ergaenzen die Basisfelder.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    # Gesetz / Verordnung / Verwaltungsanweisung / Rechtsprechung /
    # Fachliteratur / Interne Leitlinie / Sonstiges (validiert in
    # app/sources/schema.py) - "Verwaltungsanweisung" (z. B. BMF-Schreiben)
    # bewusst als eigener Typ, da im Steuerrecht besonders relevant.
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Datum des Dokuments/der Entscheidung selbst (z. B. Erlass-/Urteilsdatum).
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    retrieved_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    # entwurf / freigegeben / veraltet - endgueltiges Freigabekonzept aus
    # Prompt 14 (siehe app/sources/service.py).
    approval_level: Mapped[str] = mapped_column(
        String(32), default="entwurf", nullable=False
    )
    # Welcher SourceProvider diese Quelle geliefert/bestaetigt hat, z. B.
    # "manual" (Anwalt hat die Angaben selbst eingegeben und geprueft).
    provider_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
