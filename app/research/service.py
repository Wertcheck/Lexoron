"""LegalResearchService – Recherche-Workflow.

Ablauf:
1. `generate_queries_from_matter`: leitet deterministisch Suchfragen aus
   Aktenmetadaten ab (Titel, Fachgebiet) - kein LLM (siehe __init__.py).
2. `research`: fragt AUSSCHLIESSLICH freigegebene Rechtsquellen
   (`DocumentSearchService.search_sources`, Prompt 11/14/15) ab und
   reichert jeden Treffer mit dem vollständigen Quellenbeleg an (nie nur
   einen Score/Snippet ohne Herkunft).
3. Bewertet, ob das Ergebnis "ausreichend belegt" ist - explizit, nicht
   nur implizit aus einer leeren Liste ableitbar.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditEvent, Matter, Source
from app.research.schema import LegalResearchFinding, LegalResearchResult
from app.search.service import DocumentSearchService


class LegalResearchService:
    def __init__(
        self, search_service: DocumentSearchService, *, min_score_for_sufficient: float
    ) -> None:
        self.search_service = search_service
        self.min_score_for_sufficient = min_score_for_sufficient

    def generate_queries_from_matter(self, matter: Matter) -> list[str]:
        """Deterministische Query-Ableitung aus Aktenmetadaten - KEINE
        KI-generierte Formulierung (siehe Moduldocstring)."""
        queries: list[str] = []
        if matter.title and matter.title.strip():
            queries.append(matter.title.strip())
        if matter.practice_area and matter.practice_area.strip():
            queries.append(matter.practice_area.strip())
        if (
            matter.title
            and matter.practice_area
            and matter.title.strip()
            and matter.practice_area.strip()
        ):
            queries.append(f"{matter.title.strip()} {matter.practice_area.strip()}")

        # Deduplizieren, Reihenfolge erhalten.
        seen: set[str] = set()
        unique_queries: list[str] = []
        for query in queries:
            if query not in seen:
                seen.add(query)
                unique_queries.append(query)
        return unique_queries

    def research(
        self, query: str, db: Session, *, source_type: str | None = None
    ) -> LegalResearchResult:
        search_results = self.search_service.search_sources(
            query, db, source_type=source_type
        )

        findings: list[LegalResearchFinding] = []
        for result in search_results:
            source = db.query(Source).filter_by(id=result.entity_id).first()
            if source is None:
                # Verwaiste Embedding-Zeile (Quelle wurde geloescht) -
                # UEBERSPRINGEN statt eines Ergebnisses ohne echten Beleg.
                continue
            findings.append(
                LegalResearchFinding(
                    source_id=source.id,
                    title=source.title,
                    source_type=source.source_type,
                    reference=source.reference,
                    url=source.url,
                    document_date=source.document_date,
                    snippet=result.snippet,
                    score=result.score,
                    match_type=result.match_type,
                )
            )

        sufficiently_supported = any(
            f.score >= self.min_score_for_sufficient for f in findings
        )

        if sufficiently_supported:
            best = max(findings, key=lambda f: f.score)
            reasoning = (
                f"Ausreichend belegt: {len(findings)} freigegebene Quelle(n) "
                f"gefunden, bester Treffer '{best.title}' (Score {best.score:.2f})."
            )
        elif findings:
            reasoning = (
                f"Nicht ausreichend belegt: {len(findings)} Quelle(n) mit "
                f"schwachem Bezug gefunden (bester Score "
                f"{max(f.score for f in findings):.2f}, unterhalb der "
                f"Schwelle {self.min_score_for_sufficient}). Manuelle "
                "Recherche erforderlich."
            )
        else:
            reasoning = (
                "Nicht ausreichend belegt: keine freigegebene Rechtsquelle "
                "zu dieser Suchanfrage gefunden. Manuelle Recherche "
                "erforderlich - es wurde KEINE Fundstelle erfunden."
            )

        return LegalResearchResult(
            query=query,
            findings=findings,
            sufficiently_supported=sufficiently_supported,
            reasoning=reasoning,
        )

    def research_for_matter(
        self,
        matter: Matter,
        db: Session,
        *,
        source_type: str | None = None,
        actor: str = "system",
    ) -> list[LegalResearchResult]:
        queries = self.generate_queries_from_matter(matter)
        results = [
            self.research(query, db, source_type=source_type) for query in queries
        ]

        db.add(
            AuditEvent(
                entity_type="Matter",
                entity_id=matter.id,
                event_type="legal_research_performed",
                actor=actor,
                details=(
                    f"{len(queries)} Suchanfrage(n) ausgeführt, "
                    f"{sum(1 for r in results if r.sufficiently_supported)} "
                    f"von {len(results)} ausreichend belegt."
                ),
            )
        )
        db.commit()
        return results
