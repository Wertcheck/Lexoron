"""Law – Gesetzeswerk (z. B. "BGB", "StGB") der digitalen Gesetzesbibliothek
(20.08., siehe app/laws/ und app/web/laws_router.py).

WICHTIG (Urheberrecht, § 5 UrhG): Gesetzestexte sind "amtliche Werke" und
GENIESSEN KEINEN URHEBERRECHTLICHEN SCHUTZ - die wörtliche Wiedergabe von
Paragraphentexten hier ist rechtlich unbedenklich. Das betrifft aber nur
die urheberrechtliche Zulässigkeit, NICHT die inhaltliche Vollständigkeit/
Aktualität: die Bibliothek startet mit einer bewusst KLEINEN, manuell
kuratierten Auswahl besonders bekannter, seit Jahrzehnten kaum veränderter
Kernvorschriften (siehe app/laws/fixtures/) - kein vollständiger, live
aktualisierter Gesetzestext (Grundregel "Unsicherheit explizit markieren",
siehe CLAUDE.md) - siehe die entsprechenden Hinweise in
templates/law_library.html.

Inhalte entstehen AUSSCHLIESSLICH über den kontrollierten Import
(`app/laws/service.py: import_law_fixture_data`), NIE automatisch durch
die KI generiert - gleiches Prinzip wie bei `Source`
(app/models/source.py: "Die KI darf keine Quelle erfinden").
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Law(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "laws"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # Bewusst OHNE order_by hier: "§ 13" vs. "§ 2" sortiert als String
    # lexikografisch falsch (13 vor 2) - die numerisch korrekte Sortierung
    # uebernimmt app/laws/service.py: sort_sections_naturally beim
    # tatsaechlichen Abruf, nicht die Beziehung selbst.
    sections: Mapped[list["LawSection"]] = relationship(
        back_populates="law", cascade="all, delete-orphan"
    )
