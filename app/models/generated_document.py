"""GeneratedDocument – aus einer `DocumentTemplate` für EINE konkrete Akte
generierter Schriftsatz (Block 3, 20.08.).

`matter_id` ist Pflicht (Aktenisolation - jede Generierung bezieht sich
auf genau eine Akte, kein aktenübergreifendes Sammeldokument). `template_id`
ist NULLABLE und OHNE Kaskade: wird die Ursprungsvorlage später gelöscht,
bleibt das bereits generierte Dokument unangetastet erhalten (gleiches
Prinzip wie bei `Client.matters`/gesetzlichen Aufbewahrungspflichten,
siehe app/models/client.py) - `DocumentTemplateService.delete_template`
verweigert das Löschen ohnehin, solange noch referenzierende
`GeneratedDocument`-Zeilen existieren (siehe app/document_generator/
service.py).

`content` ist der tatsächlich editierbare Text (nach Platzhalter-
Befüllung) - die Vorschau-/Bearbeitungsseite schreibt Änderungen direkt
hierhin, das Original (`DocumentTemplate.content`) bleibt unverändert.
`unresolved_placeholders_json` hält die bei der Generierung NICHT
auflösbaren Platzhalter fest (JSON-Liste) - bleibt so auch nach einem
Seiten-Reload sichtbar (CLAUDE.md: "Unsicherheit explizit markieren")."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GeneratedDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "generated_documents"

    template_id: Mapped[str | None] = mapped_column(
        ForeignKey("document_templates.id"), nullable=True, index=True
    )
    matter_id: Mapped[str] = mapped_column(ForeignKey("matters.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    unresolved_placeholders_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by_actor: Mapped[str | None] = mapped_column(String(128), nullable=True)

    matter: Mapped["Matter"] = relationship()
    template: Mapped["DocumentTemplate | None"] = relationship()
