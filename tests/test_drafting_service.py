"""Tests fuer app/drafting/service.py (Prompt 17).

Nutzt FakeEmbeddingProvider (kein echter Modell-Download) und einen Fake
ClaudeWritingProvider (kein echter API-Aufruf)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ai_providers.claude_writing_provider import ClaudeWritingResult
from app.ai_providers.local_ai_provider import RuleBasedLocalAIProvider
from app.drafting.service import DraftingService
from app.models import ApiCallLog, AuditEvent, Client, Deadline, Draft, DraftKnowledgeItemLink, DraftSourceLink, KnowledgeItem, Matter, Source
from app.models.base import Base
from app.privacy.gateway import ClaudePrivacyGateway
from app.privacy.gateway_schema import ClaudeRequestPayload
from app.research.service import LegalResearchService
from app.search.service import DocumentSearchService
from tests.fake_embedding_provider import FakeEmbeddingProvider


class FakeClaudeWritingProvider:
    def __init__(self, response_text: str = "Formulierte Antwort.") -> None:
        self.response_text = response_text

    def write(self, payload: ClaudeRequestPayload) -> ClaudeWritingResult:
        return ClaudeWritingResult(text=self.response_text, token_count=99)


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


def _matter(db: Session, client_name: str = "Max Mustermann", title: str = "Testakte", **kwargs) -> Matter:
    client = Client(name=client_name)
    matter = Matter(client=client, title=title, **kwargs)
    db.add_all([client, matter])
    db.commit()
    return matter


def _service(
    writing_provider=None, min_score: float = 0.0
) -> tuple[DraftingService, DocumentSearchService]:
    search_service = DocumentSearchService(FakeEmbeddingProvider())
    research_service = LegalResearchService(search_service, min_score_for_sufficient=min_score)
    service = DraftingService(
        RuleBasedLocalAIProvider(),
        research_service,
        search_service,
        ClaudePrivacyGateway(),
        writing_provider or FakeClaudeWritingProvider(),
        model_name="claude-sonnet-5",
    )
    return service, search_service


def test_empty_matter_id_auto_creates_matter(db_session: Session) -> None:
    """Schriftsatz-Generator (20.08.): eine leere/fehlende matter_id wirft
    KEINEN Fehler mehr, sondern legt automatisch Mandant+Akte an, damit der
    Entwurf trotzdem gespeichert werden kann (Draft.matter_id ist NICHT
    nullable)."""
    assert db_session.query(Matter).count() == 0
    service, _ = _service()

    # Bewusst EIN Wort als Titel - zwei aufeinanderfolgende grossgeschriebene
    # Woerter wuerden vom SecurityCheckService als moegliche unerkannte
    # Namen/Entitaeten markiert (_find_possible_unrecognized_names, siehe
    # app/privacy/security_check.py) und den Aufruf blockieren - hier soll
    # ausschliesslich die Auto-Create-Verdrahtung getestet werden.
    result = service.create_draft(
        "", "formulate_draft", db_session, new_matter_title="Schnellentwurfsakte"
    )

    assert result.success is True
    matter = db_session.query(Matter).one()
    assert matter.title == "Schnellentwurfsakte"
    persisted = db_session.query(Draft).filter_by(id=result.draft_id).first()
    assert persisted.matter_id == matter.id


def test_none_matter_id_auto_creates_matter_with_default_title(db_session: Session) -> None:
    service, _ = _service()

    result = service.create_draft(None, "formulate_draft", db_session)

    assert result.success is True
    matter = db_session.query(Matter).one()
    assert "Schnellentwurf" in matter.title
    assert matter.client.name == "Ohne Mandantenzuordnung"


def test_auto_created_matter_logs_audit_event(db_session: Session) -> None:
    service, _ = _service()

    service.create_draft(None, "formulate_draft", db_session, actor="anwalt@kanzlei.test")

    matter = db_session.query(Matter).one()
    events = db_session.query(AuditEvent).filter_by(
        entity_id=matter.id, event_type="matter_auto_created"
    ).all()
    assert len(events) == 1
    assert events[0].actor == "anwalt@kanzlei.test"


def test_raises_for_unknown_matter(db_session: Session) -> None:
    service, _ = _service()
    with pytest.raises(ValueError):
        service.create_draft("nicht-vorhanden", "formulate_draft", db_session)


def test_successful_draft_is_persisted(db_session: Session) -> None:
    matter = _matter(db_session, title="Testakte")
    service, _ = _service()

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    assert result.success is True
    assert result.draft_id is not None
    persisted = db_session.query(Draft).filter_by(id=result.draft_id).first()
    assert persisted is not None
    assert persisted.status == "draft"
    assert persisted.content == result.draft_text


def test_draft_creation_logs_audit_event(db_session: Session) -> None:
    matter = _matter(db_session, title="Testakte")
    service, _ = _service()

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    events = db_session.query(AuditEvent).filter_by(
        entity_id=result.draft_id, event_type="draft_created"
    ).all()
    assert len(events) == 1


def test_source_list_contains_matching_approved_source(db_session: Session) -> None:
    matter = _matter(db_session, title="Einspruch Steuerbescheid")
    service, search_service = _service(min_score=0.0)
    source = Source(
        title="Einspruch Steuerbescheid Regelung",
        source_type="Gesetz",
        reference="§ 355 AO",
        approval_level="freigegeben",
    )
    db_session.add(source)
    db_session.commit()
    search_service.index_source(source, db_session)

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    assert any(s.source_id == source.id for s in result.source_list)
    assert any(s.reference == "§ 355 AO" for s in result.source_list)


def test_knowledge_items_used_contains_matching_approved_item(db_session: Session) -> None:
    matter = _matter(db_session, title="Einspruch Steuerbescheid")
    service, search_service = _service()
    knowledge_item = KnowledgeItem(
        title="Einspruch Steuerbescheid Baustein",
        content="Textbaustein Einspruch Steuerbescheid",
        approval_status="approved",
    )
    db_session.add(knowledge_item)
    db_session.commit()
    search_service.index_knowledge_item(knowledge_item, db_session)

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    assert any(k.knowledge_item_id == knowledge_item.id for k in result.knowledge_items_used)


def test_used_source_is_persisted_as_draft_source_link(db_session: Session) -> None:
    """Prompt 24: die tatsaechliche Verwendung wird persistiert, nicht nur
    transient im DraftingResult zurueckgegeben (Grundlage fuer das
    Quellen-Panel im Dashboard)."""
    matter = _matter(db_session, title="Einspruch Steuerbescheid")
    service, search_service = _service(min_score=0.0)
    source = Source(
        title="Einspruch Steuerbescheid Regelung",
        source_type="Gesetz",
        reference="§ 355 AO",
        approval_level="freigegeben",
    )
    db_session.add(source)
    db_session.commit()
    search_service.index_source(source, db_session)

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    links = db_session.query(DraftSourceLink).filter_by(draft_id=result.draft_id).all()
    assert len(links) == 1
    assert links[0].source_id == source.id


def test_used_knowledge_item_is_persisted_as_draft_knowledge_item_link(
    db_session: Session,
) -> None:
    matter = _matter(db_session, title="Einspruch Steuerbescheid")
    service, search_service = _service()
    knowledge_item = KnowledgeItem(
        title="Einspruch Steuerbescheid Baustein",
        content="Textbaustein Einspruch Steuerbescheid",
        approval_status="approved",
    )
    db_session.add(knowledge_item)
    db_session.commit()
    search_service.index_knowledge_item(knowledge_item, db_session)

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    links = (
        db_session.query(DraftKnowledgeItemLink).filter_by(draft_id=result.draft_id).all()
    )
    assert len(links) == 1
    assert links[0].knowledge_item_id == knowledge_item.id


def test_reference_links_are_not_shared_across_versions(db_session: Session) -> None:
    """Jede Version bekommt EIGENE Links - keine Wiederverwendung."""
    matter = _matter(db_session, title="Einspruch Steuerbescheid")
    service, search_service = _service(min_score=0.0)
    source = Source(
        title="Einspruch Steuerbescheid Regelung",
        source_type="Gesetz",
        reference="§ 355 AO",
        approval_level="freigegeben",
    )
    db_session.add(source)
    db_session.commit()
    search_service.index_source(source, db_session)

    first = service.create_draft(matter.id, "formulate_draft", db_session)
    first_draft = db_session.query(Draft).filter_by(id=first.draft_id).first()
    second = service.create_draft(
        matter.id, "improve_draft", db_session, previous_draft=first_draft
    )

    first_links = db_session.query(DraftSourceLink).filter_by(draft_id=first.draft_id).all()
    second_links = db_session.query(DraftSourceLink).filter_by(draft_id=second.draft_id).all()
    assert len(first_links) == 1
    assert len(second_links) == 1
    assert first_links[0].id != second_links[0].id


def test_no_sources_or_knowledge_items_means_no_links(db_session: Session) -> None:
    matter = _matter(db_session, title="Völlig unbekanntes Thema ohne Treffer xyz123")
    service, _ = _service()

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    assert db_session.query(DraftSourceLink).filter_by(draft_id=result.draft_id).count() == 0
    assert (
        db_session.query(DraftKnowledgeItemLink).filter_by(draft_id=result.draft_id).count()
        == 0
    )


def test_insufficient_research_becomes_open_review_point(db_session: Session) -> None:
    matter = _matter(db_session, title="Völlig unbekanntes Thema ohne Quelle")
    service, _ = _service()

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    assert any("Nicht ausreichend belegt" in point for point in result.open_review_points)


def test_unreviewed_deadline_becomes_uncertainty(db_session: Session) -> None:
    matter = _matter(db_session, title="Testakte")
    deadline = Deadline(matter=matter, source_text="Frist am 15.03.2027", confidence=0.4)
    db_session.add(deadline)
    db_session.commit()
    service, _ = _service()

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    assert any("unbestätigte Frist" in u for u in result.uncertainties)


def test_no_deadlines_means_no_uncertainty_about_deadlines(db_session: Session) -> None:
    matter = _matter(db_session, title="Testakte")
    service, _ = _service()

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    assert not any("Frist" in u for u in result.uncertainties)


def test_blocked_request_creates_no_draft(db_session: Session) -> None:
    matter = _matter(db_session, title="Testakte")
    from app.models import Document

    document = Document(
        matter=matter,
        file_path="/tmp/x.pdf",
        extracted_text="Bitte informieren Sie auch Herrn Peter Müller.",
    )
    db_session.add(document)
    db_session.commit()
    service, _ = _service()

    result = service.create_draft(matter.id, "formulate_draft", db_session)

    assert result.success is False
    assert result.draft_id is None
    assert len(result.blocked_reasons) > 0
    assert db_session.query(Draft).count() == 0


def test_blocked_request_is_logged_without_pii(db_session: Session) -> None:
    matter = _matter(db_session, title="Testakte")
    from app.models import Document

    document = Document(
        matter=matter,
        file_path="/tmp/x.pdf",
        extracted_text="Bitte informieren Sie auch Herrn Peter Müller.",
    )
    db_session.add(document)
    db_session.commit()
    service, _ = _service()

    service.create_draft(matter.id, "formulate_draft", db_session)

    logs = db_session.query(ApiCallLog).filter_by(result_status="blocked").all()
    assert len(logs) == 1
    assert "Peter" not in (logs[0].error_status or "")


def test_successful_call_is_logged_with_token_count(db_session: Session) -> None:
    matter = _matter(db_session, title="Testakte")
    service, _ = _service()

    service.create_draft(matter.id, "formulate_draft", db_session)

    logs = db_session.query(ApiCallLog).filter_by(result_status="success").all()
    assert len(logs) == 1
    assert logs[0].token_count == 99


def test_context_never_contains_data_from_other_matter(db_session: Session) -> None:
    """Aktenisolation - dasselbe wiederkehrende Muster wie im gesamten Projekt."""
    from app.models import Document

    matter_a = _matter(db_session, client_name="Mandant A", title="Akte A")
    matter_b = _matter(db_session, client_name="Mandant B", title="Akte B")
    doc_a = Document(matter=matter_a, file_path="/tmp/a.pdf", extracted_text="Geheimer Vertrag Akte A wurde geprüft.")
    doc_b = Document(matter=matter_b, file_path="/tmp/b.pdf", extracted_text="Geheimer Vertrag Akte B wurde geprüft.")
    db_session.add_all([doc_a, doc_b])
    db_session.commit()

    writing_provider = FakeClaudeWritingProvider()
    service, _ = _service(writing_provider)
    service.create_draft(matter_a.id, "formulate_draft", db_session)

    draft = db_session.query(Draft).filter_by(matter_id=matter_a.id).first()
    assert draft is not None
    # Die andere Akte darf ueberhaupt nicht in dieser Aktion beruehrt worden sein.
    assert db_session.query(Draft).filter_by(matter_id=matter_b.id).count() == 0
