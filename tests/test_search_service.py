"""Tests fuer app/search/service.py (Prompt 11).

Nutzt FakeEmbeddingProvider (siehe tests/fake_embedding_provider.py) statt
eines echten Modells - kein Netzwerkzugriff noetig. Der Schwerpunkt liegt
auf der Isolationsgarantie: Dokumentensuche darf NIE ueber die Grenze
einer Akte hinweg Ergebnisse liefern."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Client, Document, KnowledgeItem, Matter
from app.models.base import Base
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


def _matter(db: Session, title: str = "Testakte") -> Matter:
    client = Client(name="Testmandant")
    matter = Matter(client=client, title=title)
    db.add_all([client, matter])
    db.commit()
    return matter


def _service() -> DocumentSearchService:
    return DocumentSearchService(FakeEmbeddingProvider())


def test_fulltext_match_within_matter_is_found(db_session: Session) -> None:
    matter = _matter(db_session)
    document = Document(
        file_path="/tmp/x.pdf",
        matter_id=matter.id,
        extracted_text="Der Mietvertrag wurde am 01.01.2027 gekündigt.",
    )
    db_session.add(document)
    db_session.commit()

    results = _service().search_within_matter(matter.id, "Mietvertrag", db_session)

    assert len(results) == 1
    assert results[0].entity_id == document.id
    assert results[0].match_type == "fulltext"


def test_document_from_other_matter_is_never_returned(db_session: Session) -> None:
    """Kernanforderung aus Prompt 11: strikte Aktenisolation."""
    matter_a = _matter(db_session, title="Akte A")
    matter_b = _matter(db_session, title="Akte B")
    document_a = Document(
        file_path="/tmp/a.pdf", matter_id=matter_a.id, extracted_text="Kündigung Mietvertrag"
    )
    document_b = Document(
        file_path="/tmp/b.pdf", matter_id=matter_b.id, extracted_text="Kündigung Mietvertrag"
    )
    db_session.add_all([document_a, document_b])
    db_session.commit()

    results = _service().search_within_matter(matter_a.id, "Kündigung", db_session)

    assert len(results) == 1
    assert results[0].entity_id == document_a.id
    assert results[0].matter_id == matter_a.id


def test_document_without_matter_is_not_found_via_matter_search(
    db_session: Session,
) -> None:
    """Ein noch nicht zugeordnetes Dokument (matter_id=None) darf bei
    KEINER Aktensuche auftauchen - auch nicht versehentlich."""
    matter = _matter(db_session)
    unassigned_document = Document(
        file_path="/tmp/unassigned.pdf",
        matter_id=None,
        extracted_text="Kündigung Mietvertrag",
    )
    db_session.add(unassigned_document)
    db_session.commit()

    results = _service().search_within_matter(matter.id, "Kündigung", db_session)

    assert results == []


def test_metadata_filter_by_document_type(db_session: Session) -> None:
    matter = _matter(db_session)
    invoice = Document(
        file_path="/tmp/r.pdf",
        matter_id=matter.id,
        extracted_text="Testinhalt Rechnung",
        classified_type="Rechnung",
    )
    contract = Document(
        file_path="/tmp/v.pdf",
        matter_id=matter.id,
        extracted_text="Testinhalt Vertrag",
        classified_type="Vertrag",
    )
    db_session.add_all([invoice, contract])
    db_session.commit()

    results = _service().search_within_matter(
        matter.id, "Testinhalt", db_session, document_type="Rechnung"
    )

    assert len(results) == 1
    assert results[0].entity_id == invoice.id


def test_semantic_search_finds_similar_wording(db_session: Session) -> None:
    """FakeEmbeddingProvider basiert auf gemeinsamen Wörtern - ein Dokument
    mit vielen gemeinsamen Wörtern zur Anfrage sollte semantisch gefunden
    werden, auch ohne exakten Substring-Treffer."""
    matter = _matter(db_session)
    document = Document(
        file_path="/tmp/x.pdf",
        matter_id=matter.id,
        extracted_text="mietvertrag kündigung frist wohnung berlin",
    )
    db_session.add(document)
    db_session.commit()
    _service().index_document(document, db_session)

    results = _service().search_within_matter(
        matter.id, "mietvertrag kündigung frist", db_session
    )

    assert len(results) == 1
    assert results[0].match_type in {"semantic", "hybrid"}


def test_search_result_always_references_concrete_document(
    db_session: Session,
) -> None:
    matter = _matter(db_session)
    document = Document(
        file_path="/tmp/x.pdf", matter_id=matter.id, extracted_text="Testinhalt Klage"
    )
    db_session.add(document)
    db_session.commit()

    results = _service().search_within_matter(matter.id, "Klage", db_session)

    assert results[0].entity_id == document.id
    assert results[0].entity_type == "Document"


def test_knowledge_base_search_only_returns_approved_items(
    db_session: Session,
) -> None:
    approved = KnowledgeItem(
        title="Freigegebener Baustein",
        content="Textbaustein zur Kündigung eines Mietvertrags",
        approval_status="approved",
    )
    pending = KnowledgeItem(
        title="Ungeprüfter Baustein",
        content="Textbaustein zur Kündigung eines Mietvertrags",
        approval_status="pending",
    )
    db_session.add_all([approved, pending])
    db_session.commit()

    service = _service()
    service.index_knowledge_item(approved, db_session)
    service.index_knowledge_item(pending, db_session)  # sollte No-Op sein

    results = service.search_knowledge_base("Kündigung Mietvertrag", db_session)

    assert len(results) == 1
    assert results[0].entity_id == approved.id


def test_knowledge_base_search_never_returns_documents(db_session: Session) -> None:
    """Wissensbasis-Suche darf niemals Mandantendokumente liefern."""
    matter = _matter(db_session)
    document = Document(
        file_path="/tmp/x.pdf", matter_id=matter.id, extracted_text="Kündigung Mietvertrag"
    )
    db_session.add(document)
    db_session.commit()

    results = _service().search_knowledge_base("Kündigung Mietvertrag", db_session)

    assert all(r.entity_type != "Document" for r in results)


def test_no_matter_scoped_search_method_exists_without_matter_id() -> None:
    """Architektonischer Schutz: es darf keine Methode geben, die
    Dokumente ohne matter_id-Argument durchsucht (Ausnahme: die separate
    Wissensbasis-Suche, die bewusst nie Dokumente liefert)."""
    import inspect

    signature = inspect.signature(DocumentSearchService.search_within_matter)
    assert "matter_id" in signature.parameters

    public_methods = [
        name
        for name in dir(DocumentSearchService)
        if not name.startswith("_") and callable(getattr(DocumentSearchService, name))
    ]
    # Alle "search_"-Methoden ausser der Wissensbasis-Suche muessen
    # matter_id verlangen.
    for method_name in public_methods:
        if method_name.startswith("search_") and method_name != "search_knowledge_base":
            sig = inspect.signature(getattr(DocumentSearchService, method_name))
            assert "matter_id" in sig.parameters, (
                f"{method_name} erlaubt Dokumentensuche ohne matter_id!"
            )
