"""DraftFeedbackService – Feedback speichern und (getrennt) zu Kanzleiwissen befördern.

Zwei bewusst getrennte Methoden:
- `record_feedback`: speichert IMMER einen `DraftFeedback`-Schnappschuss
  (Original, ggf. Änderung, Kommentar, Status). Bei "approved_with_edits"
  entsteht die Änderung seit Prompt 23 als NEUE `Draft`-Version (siehe
  `app/drafting/versioning.py: create_new_draft_version`) - die
  ursprüngliche, vom Anwalt bewertete Version wird NIE überschrieben,
  weder inhaltlich noch im Status. Das ist reine Protokollierung/
  Statuspflege - NICHTS davon fließt automatisch in die
  Kanzlei-Wissensbasis ein.
- `promote_to_knowledge`: separater, expliziter Aufruf (siehe Konzept
  Prompt 13, wörtlich: "Baue einen expliziten Workflow 'als Kanzleiwissen
  freigeben' ein"). Legt über `KnowledgeItemService.import_item` einen
  NEUEN, weiterhin `pending` Wissenseintrag an - auch eine bewusste
  Übernahme durchläuft die normale Freigabepflicht aus Prompt 12 erneut,
  wird also nicht dadurch schon zu genehmigtem Wissen.

WICHTIG (Prompt 23, Abgrenzung zu `AttorneyInstruction`): `DraftFeedback`
bleibt ausschließlich die anwaltliche BEWERTUNG/POSITION zu einem bereits
vorliegenden Entwurf (rückblickend). Ein konkreter Arbeitsauftrag an die
NÄCHSTE Version ("§ 286 BGB berücksichtigen") ist KEIN Feedback in diesem
Sinne, sondern eine `AttorneyInstruction`
(siehe app/attorney_instructions/service.py) - beide Konzepte bewusst
getrennt gehalten, nicht ineinander integriert.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.drafting.versioning import create_manual_edit_version
from app.feedback.schema import DraftFeedbackInput, DraftFeedbackResult
from app.knowledge.schema import KnowledgeItemImport
from app.knowledge.service import KnowledgeItemService
from app.models import AuditEvent, Draft, DraftFeedback, KnowledgeItem

# approval_status (DraftFeedback) -> Draft.status (siehe app/models/draft.py:
# draft/legal_review/approved/rejected)
_DRAFT_STATUS_BY_APPROVAL_STATUS = {
    "approved": "approved",
    "approved_with_edits": "approved",
    "rejected": "rejected",
}
# Eigene, spezifische Audit-Event-Typen je Ausgang (zusätzlich zum
# weiterhin geschriebenen generischen "draft_feedback_recorded") - siehe
# Vorgabe des Anwalts: "Entwurf freigegeben" / "Entwurf zurückgewiesen"
# sollen im Audit-Log als eigene, gezielt abfragbare Ereignisse erscheinen.
_OUTCOME_EVENT_TYPE = {
    "approved": "draft_approved",
    "approved_with_edits": "draft_approved",
    "rejected": "draft_rejected",
}


class DraftFeedbackService:
    def __init__(self, knowledge_service: KnowledgeItemService | None = None) -> None:
        self.knowledge_service = knowledge_service or KnowledgeItemService()

    def record_feedback(
        self, draft: Draft, data: DraftFeedbackInput, db: Session, *, actor: str
    ) -> DraftFeedbackResult:
        original_content = draft.content

        feedback = DraftFeedback(
            draft_id=draft.id,
            original_content=original_content,
            edited_content=data.edited_content,
            comment=data.comment,
            approval_status=data.approval_status,
            actor=actor,
        )
        db.add(feedback)

        new_draft: Draft | None = None
        # entity_id fuer das Freigabe-/Ablehnungs-Event: bei einer Bearbeitung
        # ist das die NEUE Version (die tatsaechlich freigegeben wird), sonst
        # die unveraendert bestehende.
        outcome_entity_id = draft.id

        if data.approval_status == "approved_with_edits":
            # WICHTIG: die bestehende `draft`-Zeile wird NICHT veraendert
            # (weder content noch status) - eine manuelle Aenderung erzeugt
            # immer eine neue Version, siehe app/drafting/versioning.py.
            new_draft = create_manual_edit_version(
                db,
                previous_draft=draft,
                new_content=data.edited_content,  # type: ignore[arg-type]
                status="approved",
                actor=actor,
                details=(
                    f"Neue Version durch manuelle Bearbeitung "
                    f"(Feedback-Grundlage: Draft {draft.id})"
                ),
            )
            outcome_entity_id = new_draft.id
        else:
            # Reine Bewertung ohne Inhaltsaenderung - keine neue Version
            # noetig, der Status wird auf DERSELBEN Zeile aktualisiert (kein
            # Inhalts-Overwrite, siehe Modul-Docstring).
            draft.status = _DRAFT_STATUS_BY_APPROVAL_STATUS[data.approval_status]

        db.add(
            AuditEvent(
                entity_type="Draft",
                entity_id=draft.id,
                event_type="draft_feedback_recorded",
                actor=actor,
                details=(
                    f"Feedback: {data.approval_status}"
                    + (f" - Kommentar: {data.comment}" if data.comment else "")
                ),
            )
        )
        db.add(
            AuditEvent(
                entity_type="Draft",
                entity_id=outcome_entity_id,
                event_type=_OUTCOME_EVENT_TYPE[data.approval_status],
                actor=actor,
                details=(
                    f"Ausgang: {data.approval_status}"
                    + (f" - Kommentar: {data.comment}" if data.comment else "")
                ),
            )
        )
        db.commit()
        db.refresh(feedback)
        db.refresh(draft)
        if new_draft is not None:
            db.refresh(new_draft)
        return DraftFeedbackResult(feedback=feedback, draft=draft, new_draft=new_draft)

    def promote_to_knowledge(
        self,
        feedback: DraftFeedback,
        db: Session,
        *,
        title: str,
        actor: str,
        category: str | None = None,
        practice_area: str | None = None,
        use_edited_content: bool = True,
    ) -> KnowledgeItem:
        """Expliziter Workflow "als Kanzleiwissen freigeben".

        Wählt standardmäßig den editierten Inhalt (die vom Anwalt
        korrigierte Fassung), falls vorhanden - fällt sonst auf den
        Originalinhalt zurück. Das Ergebnis ist IMMER ein neuer,
        `pending` Wissenseintrag (siehe KnowledgeItemService.import_item)
        - die Übernahme selbst ist keine Freigabe.
        """
        content = (
            feedback.edited_content
            if use_edited_content and feedback.edited_content
            else feedback.original_content
        )

        knowledge_item = self.knowledge_service.import_item(
            KnowledgeItemImport(
                title=title,
                content=content,
                category=category,
                practice_area=practice_area,
                source=f"Übernommen aus Entwurfs-Feedback (draft_feedback_id={feedback.id})",
            ),
            db,
            actor=actor,
        )

        db.add(
            AuditEvent(
                entity_type="DraftFeedback",
                entity_id=feedback.id,
                event_type="draft_feedback_promoted_to_knowledge",
                actor=actor,
                details=(
                    f"Als Kanzleiwissen-Kandidat übernommen: KnowledgeItem "
                    f"{knowledge_item.id} (weiterhin 'pending', erfordert "
                    "separate Freigabe)"
                ),
            )
        )
        db.commit()
        return knowledge_item
