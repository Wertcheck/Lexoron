"""DocumentTemplateService – CRUD für Dokumentvorlagen (Block 3, 20.08.).

Löschlogik: eine Vorlage, aus der bereits mindestens EIN
`GeneratedDocument` erzeugt wurde, wird NICHT gelöscht -
`DocumentTemplateHasGeneratedDocumentsError` statt eines stillen
Verwaisens der bereits generierten (und ggf. bereits versendeten)
Schriftsätze. Gleiches Prinzip wie bei `Client.matters` (siehe
app/clients/service.py: delete_client) - Fallarbeit, die bereits erzeugt
wurde, darf durch eine spätere Aufräumaktion an der Vorlage nicht ihre
Herkunft verlieren."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.document_generator.schema import DocumentTemplateInput
from app.models import AuditEvent, DocumentTemplate, GeneratedDocument


class DocumentTemplateHasGeneratedDocumentsError(Exception):
    pass


class DocumentTemplateService:
    def list_templates(self, db: Session) -> list[DocumentTemplate]:
        return db.query(DocumentTemplate).order_by(DocumentTemplate.name).all()

    def get_template(self, db: Session, template_id: str) -> DocumentTemplate | None:
        return db.get(DocumentTemplate, template_id)

    def create_template(
        self, db: Session, data: DocumentTemplateInput, *, actor: str
    ) -> DocumentTemplate:
        template = DocumentTemplate(
            name=data.name,
            category=(data.category or "").strip() or None,
            description=data.description,
            content=data.content,
            version=1,
            created_by_actor=actor,
            updated_by_actor=actor,
        )
        db.add(template)
        db.flush()
        db.add(
            AuditEvent(
                entity_type="DocumentTemplate",
                entity_id=template.id,
                event_type="document_template_created",
                actor=actor,
                details=f"Name: {data.name}",
            )
        )
        db.commit()
        db.refresh(template)
        return template

    def update_template(
        self,
        db: Session,
        template: DocumentTemplate,
        data: DocumentTemplateInput,
        *,
        actor: str,
    ) -> DocumentTemplate:
        template.name = data.name
        template.category = (data.category or "").strip() or None
        template.description = data.description
        template.content = data.content
        template.version += 1
        template.updated_by_actor = actor
        db.add(
            AuditEvent(
                entity_type="DocumentTemplate",
                entity_id=template.id,
                event_type="document_template_updated",
                actor=actor,
                details=f"Neue Version: {template.version}",
            )
        )
        db.commit()
        db.refresh(template)
        return template

    def delete_template(self, db: Session, template: DocumentTemplate, *, actor: str) -> None:
        generated_count = (
            db.query(GeneratedDocument).filter_by(template_id=template.id).count()
        )
        if generated_count > 0:
            raise DocumentTemplateHasGeneratedDocumentsError(
                f"Vorlage '{template.name}' wurde bereits {generated_count}-mal verwendet - "
                "Löschen ist gesperrt, damit generierte Dokumente ihre Herkunft behalten."
            )
        db.add(
            AuditEvent(
                entity_type="DocumentTemplate",
                entity_id=template.id,
                event_type="document_template_deleted",
                actor=actor,
                details=f"Name: {template.name}",
            )
        )
        db.delete(template)
        db.commit()
