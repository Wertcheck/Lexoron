"""DraftingService – siehe __init__.py für die Gesamteinordnung.

Ablauf:
1. Aktenkontext lokal aufbereiten (`LocalAIProvider`).
2. Zugelassene Rechtsquellen recherchieren (`LegalResearchService`,
   Prompt 15) - liefert vollständige Belege, markiert unzureichend
   belegte Anfragen als offenen Prüfpunkt.
3. Freigegebenes Kanzleiwissen suchen (`DocumentSearchService.
   search_knowledge_base`), mit Rückverfolgung zu den tatsächlichen
   `KnowledgeItem`-Zeilen.
4. Über den Privacy Gateway (Schritt 1-3) pseudonymisieren, prüfen, ggf.
   blockieren.
5. Bei Erfolg: `ClaudeWritingProvider` aufrufen, protokollieren
   (Schritt 5), lokal rekonstruieren, als `Draft` persistieren.
6. Unsicherheiten ergänzen (z. B. unbestätigte Fristen in der Akte).

KEINE Versand-Fähigkeit: dieser Service hat keine Methode, die eine
E-Mail verschickt oder einen Versand auslöst - das bleibt dem noch nicht
gebauten Postausgang (Prompt 25) und der anwaltlichen Freigabe
vorbehalten.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai_providers.claude_writing_provider import ClaudeWritingProvider
from app.ai_providers.local_ai_provider import LocalAIProvider
from app.drafting.schema import DraftingResult, KnowledgeItemReference, SourceReference
from app.drafting.versioning import create_new_draft_version
from app.models import Deadline, Draft, KnowledgeItem, Matter
from app.privacy.api_logger import ApiCallLogger
from app.privacy.gateway import ClaudePrivacyGateway
from app.research.service import LegalResearchService
from app.search.service import DocumentSearchService


class DraftingService:
    def __init__(
        self,
        local_ai: LocalAIProvider,
        research_service: LegalResearchService,
        search_service: DocumentSearchService,
        gateway: ClaudePrivacyGateway,
        writing_provider: ClaudeWritingProvider,
        *,
        api_logger: ApiCallLogger | None = None,
        model_name: str = "unknown",
    ) -> None:
        self.local_ai = local_ai
        self.research_service = research_service
        self.search_service = search_service
        self.gateway = gateway
        self.writing_provider = writing_provider
        self.api_logger = api_logger if api_logger is not None else ApiCallLogger()
        self.model_name = model_name

    def create_draft(
        self,
        matter_id: str,
        purpose: str,
        db: Session,
        *,
        stil: str | None = None,
        vorlage: str | None = None,
        attorney_anmerkungen: str | None = None,
        previous_draft: Draft | None = None,
        actor: str = "system",
    ) -> DraftingResult:
        """Erstellt eine neue Draft-Version.

        `previous_draft=None` (Standardfall): erste Version einer neuen
        Entwurfslinie (v1).

        `previous_draft=<Draft>`: Neugenerierung als FOLGEVERSION - z. B.
        angestoßen durch `AttorneyInstructionService.apply_instruction`
        (siehe app/attorney_instructions/service.py). Erzeugt IMMER eine
        NEUE `Draft`-Zeile über `create_new_draft_version`
        (app/drafting/versioning.py) - die Vorgänger-Zeile wird an keiner
        Stelle verändert.

        `attorney_anmerkungen`: unpseudonymisierter Freitext einer
        anwaltlichen Anmerkung (siebtes Allowlist-Feld, siehe
        gateway_schema.py) - durchläuft hier denselben Privacy-Gateway-
        Durchlauf wie Sachverhalt/Quellen/Vorlage, GENAU EINMAL, bevor
        irgendetwas Claude erreicht.
        """
        if not matter_id:
            raise ValueError(
                "matter_id ist erforderlich - Entwurfserstellung ohne "
                "Aktenbezug ist nicht erlaubt"
            )
        matter = db.query(Matter).filter_by(id=matter_id).first()
        if matter is None:
            raise ValueError(f"Matter {matter_id} nicht gefunden")
        if previous_draft is not None and previous_draft.matter_id != matter_id:
            raise ValueError(
                "previous_draft gehört nicht zur angegebenen Akte - "
                "Versionsketten dürfen Aktengrenzen nicht überschreiten"
            )

        preparation = self.local_ai.prepare_draft_context(matter_id, db)

        source_list, quellen_texts, open_review_points = self._gather_legal_sources(
            matter, db, actor=actor
        )
        knowledge_items_used, knowledge_texts = self._gather_knowledge_items(matter, db)

        gateway_result = self.gateway.prepare_request(
            purpose=purpose,
            sachverhalt=preparation.sachverhalt,
            argumentationspunkte=preparation.argumentationspunkte,
            quellenverweise=quellen_texts + knowledge_texts,
            stil=stil,
            vorlage=vorlage,
            anwaltliche_anmerkungen=attorney_anmerkungen,
            known_entities=preparation.known_entities,
        )

        if not gateway_result.allowed:
            self.api_logger.log_blocked(
                db,
                workflow_id=matter_id,
                model=self.model_name,
                purpose=purpose,
                reasons=gateway_result.reasons,
            )
            return DraftingResult(
                success=False,
                blocked_reasons=gateway_result.reasons,
                open_review_points=open_review_points,
            )

        try:
            writing_result = self.writing_provider.write(gateway_result.payload)
        except Exception:
            self.api_logger.log_error(
                db,
                workflow_id=matter_id,
                model=self.model_name,
                purpose=purpose,
                payload=gateway_result.payload,
            )
            return DraftingResult(
                success=False,
                blocked_reasons=["Interner Fehler bei der Textproduktion"],
                open_review_points=open_review_points,
            )

        self.api_logger.log_success(
            db,
            workflow_id=matter_id,
            model=self.model_name,
            purpose=purpose,
            payload=gateway_result.payload,
            token_count=writing_result.token_count,
        )

        reconstructed_text = self.gateway.reconstruct_response(
            writing_result.text, gateway_result.mappings
        )

        draft = self._persist_draft(
            matter_id,
            reconstructed_text,
            purpose,
            db,
            actor=actor,
            previous_draft=previous_draft,
        )
        uncertainties = self._gather_uncertainties(matter_id, db)

        return DraftingResult(
            success=True,
            draft_id=draft.id,
            draft_text=reconstructed_text,
            source_list=source_list,
            knowledge_items_used=knowledge_items_used,
            open_review_points=open_review_points,
            uncertainties=uncertainties,
        )

    def _gather_legal_sources(
        self, matter: Matter, db: Session, *, actor: str
    ) -> tuple[list[SourceReference], list[str], list[str]]:
        research_results = self.research_service.research_for_matter(
            matter, db, actor=actor
        )

        source_list: list[SourceReference] = []
        quellen_texts: list[str] = []
        open_review_points: list[str] = []
        seen_source_ids: set[str] = set()

        for result in research_results:
            if not result.sufficiently_supported:
                open_review_points.append(
                    f"Nicht ausreichend belegt: '{result.query}' – manuelle "
                    "Rechtsrecherche erforderlich."
                )
            for finding in result.findings:
                quellen_texts.append(
                    f"{finding.title} ({finding.reference or 'ohne Fundstelle'}): "
                    f"{finding.snippet}"
                )
                if finding.source_id not in seen_source_ids:
                    seen_source_ids.add(finding.source_id)
                    source_list.append(
                        SourceReference(
                            source_id=finding.source_id,
                            title=finding.title,
                            reference=finding.reference,
                            url=finding.url,
                        )
                    )

        return source_list, quellen_texts, open_review_points

    def _gather_knowledge_items(
        self, matter: Matter, db: Session
    ) -> tuple[list[KnowledgeItemReference], list[str]]:
        query = matter.practice_area or matter.title
        results = self.search_service.search_knowledge_base(query, db)

        knowledge_items_used: list[KnowledgeItemReference] = []
        knowledge_texts: list[str] = []
        for result in results:
            item = db.query(KnowledgeItem).filter_by(id=result.entity_id).first()
            if item is None:
                continue  # verwaister Embedding-Eintrag - ueberspringen
            knowledge_items_used.append(
                KnowledgeItemReference(knowledge_item_id=item.id, title=item.title)
            )
            knowledge_texts.append(f"{item.title}: {result.snippet}")

        return knowledge_items_used, knowledge_texts

    def _persist_draft(
        self,
        matter_id: str,
        content: str,
        purpose: str,
        db: Session,
        *,
        actor: str,
        previous_draft: Draft | None = None,
    ) -> Draft:
        """Delegiert an `create_new_draft_version` (app/drafting/versioning.py) -
        siehe dort für die Begründung, warum das Anlegen neuer Draft-Zeilen
        an EINER zentralen Stelle gebündelt ist. `event_type` unterscheidet
        die allererste Version ("draft_created", unverändertes Verhalten)
        von einer Folgeversion durch Neugenerierung ("draft_version_created").
        """
        event_type = "draft_created" if previous_draft is None else "draft_version_created"
        details = (
            f"Entwurf erstellt (Zweck: {purpose})"
            if previous_draft is None
            else f"Neue Version durch Neugenerierung (Zweck: {purpose})"
        )
        return create_new_draft_version(
            db,
            matter_id=matter_id,
            content=content,
            previous_draft=previous_draft,
            actor=actor,
            event_type=event_type,
            details=details,
        )

    def _gather_uncertainties(self, matter_id: str, db: Session) -> list[str]:
        uncertainties: list[str] = []
        unreviewed_deadlines = (
            db.query(Deadline)
            .filter(Deadline.matter_id == matter_id, Deadline.review_status == "unreviewed")
            .all()
        )
        if unreviewed_deadlines:
            uncertainties.append(
                f"{len(unreviewed_deadlines)} unbestätigte Frist(en) in dieser Akte - "
                "vor Freigabe prüfen."
            )
        return uncertainties
