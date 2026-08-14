"""Tests fuer app/research/service.py (Prompt 15).

Nutzt FakeEmbeddingProvider - kein echter Modell-Download noetig."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import AuditEvent, Client, Matter, Source
from app.models.base import Base
from app.research.service import LegalResearchService
from app.search.service import DocumentSearchService
from tests.fake_embedding_provider import FakeEmbeddingProvider


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _service(min_score: float = 0.5) -> LegalResearchService:
    search_service = DocumentSearchService(FakeEmbeddingProvider())
    return LegalResearchService(search_service, min_score_for_sufficient=min_score)


def _matter(db: Session, **kwargs) -> Matter:
    client = Client(name="Testmandant")
    matter = Matter(client=client, **kwargs)
    db.add_all([client, matter])
    db.commit()
    return matter


def test_generate_queries_from_matter_uses_title_and_practice_area(
    db_session: Session,
) -> None:
    matter = _matter(db_session, title="Einspruch Steuerbescheid", practice_area="Steuerrecht")
    service = _service()

    queries = service.generate_queries_from_matter(matter)

    assert "Einspruch Steuerbescheid" in queries
    assert "Steuerrecht" in queries
    assert "Einspruch Steuerbescheid Steuerrecht" in queries


def test_generate_queries_deduplicates(db_session: Session) -> None:
    matter = _matter(db_session, title="Testakte", practice_area=None)
    service = _service()

    queries = service.generate_queries_from_matter(matter)

    assert queries == ["Testakte"]


def test_research_finds_approved_source_with_full_citation(
    db_session: Session,
) -> None:
    source = Source(
        title="§ 355 AO Einspruchsfrist",
        source_type="Gesetz",
        reference="§ 355 AO",
        url="https://example.test/ao-355",
        approval_level="freigegeben",
    )
    db_session.add(source)
    db_session.commit()

    service = _service(min_score=0.0)  # Fake-Provider liefert keine echte Semantik
    service.search_service.index_source(source, db_session)

    result = service.research("Einspruchsfrist", db_session)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.source_id == source.id
    assert finding.reference == "§ 355 AO"
    assert finding.url == "https://example.test/ao-355"


def test_research_never_returns_finding_without_real_source(
    db_session: Session,
) -> None:
    """Kernanforderung: jedes Finding muss auf eine tatsaechliche Source-
    Zeile verweisen - kein erfundenes Ergebnis."""
    source = Source(
        title="Testquelle", source_type="Gesetz", approval_level="freigegeben"
    )
    db_session.add(source)
    db_session.commit()

    service = _service(min_score=0.0)
    service.search_service.index_source(source, db_session)

    result = service.research("Testquelle", db_session)

    for finding in result.findings:
        persisted = db_session.query(Source).filter_by(id=finding.source_id).first()
        assert persisted is not None


def test_research_reports_not_sufficiently_supported_when_no_source_found(
    db_session: Session,
) -> None:
    service = _service()

    result = service.research("Völlig unbekanntes Thema ohne jede Quelle", db_session)

    assert result.sufficiently_supported is False
    assert result.findings == []
    assert "nicht ausreichend belegt" in result.reasoning.lower()


def test_research_reports_sufficiently_supported_with_strong_match(
    db_session: Session,
) -> None:
    source = Source(
        title="Steuerbescheid Einspruch Frist",
        source_type="Gesetz",
        reference="§ 355 AO",
        approval_level="freigegeben",
    )
    db_session.add(source)
    db_session.commit()

    service = _service(min_score=0.0)
    service.search_service.index_source(source, db_session)

    result = service.research("Steuerbescheid Einspruch Frist", db_session)

    assert result.sufficiently_supported is True
    assert "ausreichend belegt" in result.reasoning.lower()


def test_research_respects_source_type_filter(db_session: Session) -> None:
    law = Source(
        title="Gesetzestext Frist",
        source_type="Gesetz",
        approval_level="freigegeben",
    )
    admin = Source(
        title="Verwaltungsanweisung Frist",
        source_type="Verwaltungsanweisung",
        approval_level="freigegeben",
    )
    db_session.add_all([law, admin])
    db_session.commit()

    service = _service(min_score=0.0)
    service.search_service.index_source(law, db_session)
    service.search_service.index_source(admin, db_session)

    result = service.research("Frist", db_session, source_type="Gesetz")
    found_ids = {f.source_id for f in result.findings}

    assert law.id in found_ids
    assert admin.id not in found_ids


def test_research_for_matter_runs_all_generated_queries_and_logs_audit(
    db_session: Session,
) -> None:
    matter = _matter(db_session, title="Einspruch Steuerbescheid", practice_area="Steuerrecht")
    source = Source(
        title="Einspruch Steuerbescheid Regelung",
        source_type="Gesetz",
        approval_level="freigegeben",
    )
    db_session.add(source)
    db_session.commit()

    service = _service(min_score=0.0)
    service.search_service.index_source(source, db_session)

    results = service.research_for_matter(matter, db_session, actor="anwalt@kanzlei.test")

    assert len(results) == len(service.generate_queries_from_matter(matter))

    events = db_session.query(AuditEvent).filter_by(
        entity_id=matter.id, event_type="legal_research_performed"
    ).all()
    assert len(events) == 1
