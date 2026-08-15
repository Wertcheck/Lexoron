"""LocalAIProvider – Protocol + regelbasierte Implementierung.

`RuleBasedLocalAIProvider` erfindet KEINE neue Analyselogik - sie bündelt
ausschließlich bereits bestehende, getestete Bausteine (Document.
extracted_text aus Prompt 06, Deadline aus Prompt 10,
DocumentSearchService.search_knowledge_base aus Prompt 11/12) zu EINEM
Ergebnis, das direkt als Eingabe für `ClaudePrivacyGateway.prepare_request`
(Schritt 3) dient - siehe Pipeline-Diagramm in der Architekturvorgabe:
"Local AI -> ... -> Draft Preparation -> Privacy Gateway".

WICHTIG: Jede Datenbankabfrage ist strikt nach `matter_id` gefiltert -
exakt dasselbe Isolationsmuster wie in `search_within_matter` (Prompt 11)
und `PromptContextBuilder` (Prompt 16).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import Deadline, Document, Matter, Party
from app.search.service import DocumentSearchService
from app.search.utils import build_snippet

_MAX_DOCUMENT_EXCERPT_CHARS = 500
# Sicherheitsergänzung (Prompt 28): ohne Obergrenze könnte eine Akte mit
# sehr vielen (z. B. absichtlich zugeschickten) kleinen Anhängen den
# Sachverhalt und damit die Kosten/Tokenzahl jeder Claude-Anfrage
# unbegrenzt aufblähen. Begrenzung auf die neuesten N Dokumente -
# konsistent mit der bereits bestehenden Pro-Dokument-Zeichenbegrenzung.
_MAX_DOCUMENTS_IN_SACHVERHALT = 30

# Grobe, tolerante Rollen-Zuordnung fuer Party.role (Freitext, Prompt 04).
_OPPONENT_ROLE_KEYWORDS = ("gegner", "gegenseite", "beklagte", "beklagter")
_COURT_ROLE_KEYWORDS = ("gericht", "finanzamt", "behörde", "behoerde")
_LAWYER_ROLE_KEYWORDS = ("anwalt", "anwältin", "rechtsanwalt", "prozessbevollmächtigt")


@dataclass
class DraftPreparationResult:
    sachverhalt: str
    argumentationspunkte: list[str] = field(default_factory=list)
    quellenverweise: list[str] = field(default_factory=list)
    known_entities: dict[str, list[str]] = field(default_factory=dict)


class LocalAIProvider(Protocol):
    def prepare_draft_context(
        self, matter_id: str, db: Session
    ) -> DraftPreparationResult: ...


class RuleBasedLocalAIProvider:
    def __init__(self, search_service: DocumentSearchService | None = None) -> None:
        self.search_service = search_service

    def prepare_draft_context(
        self, matter_id: str, db: Session
    ) -> DraftPreparationResult:
        if not matter_id:
            raise ValueError(
                "matter_id ist erforderlich - Kontextvorbereitung ohne "
                "Aktenbezug ist nicht erlaubt"
            )

        matter = db.query(Matter).filter_by(id=matter_id).first()
        if matter is None:
            raise ValueError(f"Matter {matter_id} nicht gefunden")

        sachverhalt = self._build_sachverhalt(matter_id, matter, db)
        argumentationspunkte = self._build_argumentationspunkte(matter_id, db)
        quellenverweise = self._build_quellenverweise(matter, db)
        known_entities = self._build_known_entities(matter_id, matter, db)

        return DraftPreparationResult(
            sachverhalt=sachverhalt,
            argumentationspunkte=argumentationspunkte,
            quellenverweise=quellenverweise,
            known_entities=known_entities,
        )

    def _build_sachverhalt(self, matter_id: str, matter: Matter, db: Session) -> str:
        parts = [f"Akte: {matter.title}"]
        documents = (
            db.query(Document)
            .filter(Document.matter_id == matter_id)
            .filter(Document.extracted_text.isnot(None))
            .order_by(Document.created_at.desc())
            .limit(_MAX_DOCUMENTS_IN_SACHVERHALT)
            .all()
        )
        for document in documents:
            excerpt = build_snippet(
                document.extracted_text[:_MAX_DOCUMENT_EXCERPT_CHARS], ""
            )
            type_label = document.classified_type or "unklassifiziert"
            parts.append(f"[{type_label}] {excerpt}")
        return "\n".join(parts)

    def _build_argumentationspunkte(self, matter_id: str, db: Session) -> list[str]:
        deadlines = db.query(Deadline).filter(Deadline.matter_id == matter_id).all()
        return [
            f"Mögliche Frist ({deadline.review_status}): {deadline.source_text}"
            for deadline in deadlines
        ]

    def _build_quellenverweise(self, matter: Matter, db: Session) -> list[str]:
        if self.search_service is None:
            return []
        query = matter.practice_area or matter.title
        results = self.search_service.search_knowledge_base(query, db)
        return [result.snippet for result in results]

    def _build_known_entities(
        self, matter_id: str, matter: Matter, db: Session
    ) -> dict[str, list[str]]:
        known: dict[str, list[str]] = {"mandant": [], "gegner": [], "anwalt": [], "gericht": []}
        if matter.client and matter.client.name:
            known["mandant"].append(matter.client.name)

        parties = db.query(Party).filter(Party.matter_id == matter_id).all()
        for party in parties:
            role = (party.role or "").lower()
            if any(keyword in role for keyword in _OPPONENT_ROLE_KEYWORDS):
                known["gegner"].append(party.name)
            elif any(keyword in role for keyword in _COURT_ROLE_KEYWORDS):
                known["gericht"].append(party.name)
            elif any(keyword in role for keyword in _LAWYER_ROLE_KEYWORDS):
                known["anwalt"].append(party.name)
            else:
                known.setdefault("beteiligter", []).append(party.name)

        return {category: names for category, names in known.items() if names}
