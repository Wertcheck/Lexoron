"""DocumentTemplate – wiederverwendbare Schriftsatz-/Dokumentvorlage
(Dokumenten- und Schriftsatz-Generator, Block 3, 20.08.).

Enthält Platzhalter in eckigen Klammern (z. B. `[Mandantenname]`,
`[Aktenzeichen]`, `[Paragraf:BGB:§ 433]`) - siehe
app/document_generator/placeholders.py für die vollständige, unterstützte
Liste. Bewusst GETRENNT von `PromptTemplate` (app/models/prompt_template.py,
"Standard-Prompts"-Bibliothek): dort geht es um Textbausteine für KI-
Prompts (`{Platzhalter}`-Syntax, nie automatisch mit echten Falldaten
befüllt), hier um direkt aus der Datenbank automatisiert befüllte
Schriftsatz-/Dokumentvorlagen - zwei unterschiedliche Zwecke, zwei
unterschiedliche Platzhalter-Syntaxen, keine Vermischung.

Versionierung analog zu `PromptTemplate`: ein einfacher Zähler pro
inhaltlicher Änderung (keine Versionshistorie mehrerer Zeilen - eine
Vorlage ist immer die aktuellste)."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # z. B. "Mahnung", "Klageschrift", "Vertrag" - bewusst freier String
    # statt DB-Enum, analog zu Matter.practice_area/Client.practice_area.
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by_actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
