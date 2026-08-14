"""Tests fuer app/ai_providers/local_ai_provider.py."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ai_providers.local_ai_provider import RuleBasedLocalAIProvider
from app.models import Client, Deadline, Document, Matter, Party
from app.models.base import Base


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


def test_requires_matter_id() -> None:
    provider = RuleBasedLocalAIProvider()
    with pytest.raises(ValueError):
        provider.prepare_draft_context("", db=None)  # type: ignore[arg-type]


def test_raises_for_unknown_matter(db_session: Session) -> None:
    provider = RuleBasedLocalAIProvider()
    with pytest.raises(ValueError):
        provider.prepare_draft_context("nicht-vorhanden", db_session)


def test_sachverhalt_includes_document_excerpts(db_session: Session) -> None:
    matter = _matter(db_session, title="Testakte")
    document = Document(
        matter=matter,
        file_path="/tmp/x.pdf",
        extracted_text="Wichtiger Inhalt des Dokuments.",
        classified_type="Steuerbescheid",
    )
    db_session.add(document)
    db_session.commit()

    provider = RuleBasedLocalAIProvider()
    result = provider.prepare_draft_context(matter.id, db_session)

    assert "Testakte" in result.sachverhalt
    assert "Wichtiger Inhalt des Dokuments." in result.sachverhalt
    assert "Steuerbescheid" in result.sachverhalt


def test_argumentationspunkte_include_deadlines(db_session: Session) -> None:
    matter = _matter(db_session)
    deadline = Deadline(matter=matter, source_text="Frist am 15.03.2027", confidence=0.4)
    db_session.add(deadline)
    db_session.commit()

    provider = RuleBasedLocalAIProvider()
    result = provider.prepare_draft_context(matter.id, db_session)

    assert any("Frist am 15.03.2027" in a for a in result.argumentationspunkte)


def test_known_entities_include_client_as_mandant(db_session: Session) -> None:
    matter = _matter(db_session, client_name="Max Mustermann")
    provider = RuleBasedLocalAIProvider()

    result = provider.prepare_draft_context(matter.id, db_session)

    assert "Max Mustermann" in result.known_entities.get("mandant", [])


def test_party_with_opponent_role_is_categorized_as_gegner(db_session: Session) -> None:
    matter = _matter(db_session)
    party = Party(matter=matter, name="Erika Musterfrau", role="Gegnerin")
    db_session.add(party)
    db_session.commit()

    provider = RuleBasedLocalAIProvider()
    result = provider.prepare_draft_context(matter.id, db_session)

    assert "Erika Musterfrau" in result.known_entities.get("gegner", [])


def test_party_with_court_role_is_categorized_as_gericht(db_session: Session) -> None:
    matter = _matter(db_session)
    party = Party(matter=matter, name="Finanzamt Musterstadt", role="Behörde")
    db_session.add(party)
    db_session.commit()

    provider = RuleBasedLocalAIProvider()
    result = provider.prepare_draft_context(matter.id, db_session)

    assert "Finanzamt Musterstadt" in result.known_entities.get("gericht", [])


def test_party_without_recognized_role_goes_to_generic_category(
    db_session: Session,
) -> None:
    matter = _matter(db_session)
    party = Party(matter=matter, name="Zeuge Unbekannt", role="Zeuge")
    db_session.add(party)
    db_session.commit()

    provider = RuleBasedLocalAIProvider()
    result = provider.prepare_draft_context(matter.id, db_session)

    assert "Zeuge Unbekannt" in result.known_entities.get("beteiligter", [])


def test_context_never_contains_data_from_other_matter(db_session: Session) -> None:
    """Aktenisolation - dasselbe Muster wie bei PromptContextBuilder (Prompt 16)."""
    matter_a = _matter(db_session, client_name="Mandant A", title="Akte A")
    matter_b = _matter(db_session, client_name="Mandant B", title="Akte B")

    doc_a = Document(
        matter=matter_a, file_path="/tmp/a.pdf", extracted_text="Vertraulicher Inhalt A"
    )
    doc_b = Document(
        matter=matter_b, file_path="/tmp/b.pdf", extracted_text="Vertraulicher Inhalt B"
    )
    db_session.add_all([doc_a, doc_b])
    db_session.commit()

    provider = RuleBasedLocalAIProvider()
    result = provider.prepare_draft_context(matter_a.id, db_session)

    assert "Inhalt A" in result.sachverhalt
    assert "Inhalt B" not in result.sachverhalt
    assert "Mandant B" not in result.known_entities.get("mandant", [])


def test_no_search_service_results_in_empty_quellenverweise(db_session: Session) -> None:
    matter = _matter(db_session)
    provider = RuleBasedLocalAIProvider(search_service=None)

    result = provider.prepare_draft_context(matter.id, db_session)

    assert result.quellenverweise == []
