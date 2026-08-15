"""Tests für app/synthetic_data/ (Prompt 29)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.classification.schema import ALLOWED_DOCUMENT_TYPES
from app.models import Client, Document, Matter, Message
from app.models.base import Base
from app.synthetic_data import SCENARIOS, SyntheticDataGenerator


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


# --- Grundfunktion ---


def test_generate_case_creates_consistent_records(db_session: Session) -> None:
    generator = SyntheticDataGenerator(seed=1)
    case = generator.generate_case(db_session)

    assert case.matter.client_id == case.client.id
    assert case.message.matter_id == case.matter.id
    assert case.document.matter_id == case.matter.id
    assert case.document.message_id == case.message.id
    if case.deadline is not None:
        assert case.deadline.matter_id == case.matter.id
        assert case.deadline.document_id == case.document.id


def test_generate_case_uses_only_synthetic_email_domain(db_session: Session) -> None:
    generator = SyntheticDataGenerator(seed=2)
    case = generator.generate_case(db_session)
    # RFC 2606 reservierte Testdomain - technisch nie zustellbar.
    assert case.message.sender.endswith("@example-testdomain.invalid")


def test_generate_case_classified_type_is_valid(db_session: Session) -> None:
    generator = SyntheticDataGenerator(seed=3)
    for scenario in SCENARIOS:
        case = generator.generate_case(db_session, scenario_key=scenario.key)
        assert case.document.classified_type in ALLOWED_DOCUMENT_TYPES


def test_unknown_scenario_key_raises(db_session: Session) -> None:
    generator = SyntheticDataGenerator(seed=4)
    with pytest.raises(ValueError):
        generator.generate_case(db_session, scenario_key="nicht-vorhanden")


# --- Determinismus (wichtig für den Benchmark aus Prompt 30) ---


def test_same_seed_produces_identical_case_content() -> None:
    engine_a = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine_a)
    db_a = sessionmaker(bind=engine_a)()
    case_a = SyntheticDataGenerator(seed=99).generate_case(db_a)

    engine_b = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine_b)
    db_b = sessionmaker(bind=engine_b)()
    case_b = SyntheticDataGenerator(seed=99).generate_case(db_b)

    assert case_a.client.name == case_b.client.name
    assert case_a.matter.title == case_b.matter.title
    assert case_a.message.subject == case_b.message.subject
    assert case_a.document.extracted_text == case_b.document.extracted_text

    db_a.close()
    db_b.close()
    engine_a.dispose()
    engine_b.dispose()


def test_different_seeds_produce_different_cases(db_session: Session) -> None:
    case_a = SyntheticDataGenerator(seed=1).generate_case(db_session)
    case_b = SyntheticDataGenerator(seed=2).generate_case(db_session)
    assert case_a.client.name != case_b.client.name


# --- generate_many ---


def test_generate_many_creates_requested_count(db_session: Session) -> None:
    generator = SyntheticDataGenerator(seed=5)
    cases = generator.generate_many(db_session, 12)
    assert len(cases) == 12
    assert db_session.query(Matter).count() == 12
    assert db_session.query(Client).count() == 12
    assert db_session.query(Message).count() == 12
    assert db_session.query(Document).count() == 12


def test_generate_many_covers_all_scenarios_when_count_exceeds_scenario_count(
    db_session: Session,
) -> None:
    generator = SyntheticDataGenerator(seed=6)
    cases = generator.generate_many(db_session, len(SCENARIOS) * 3)
    used_scenarios = {c.scenario_key for c in cases}
    assert used_scenarios == {s.key for s in SCENARIOS}


def test_generate_many_is_deterministic_with_seed() -> None:
    engine_a = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine_a)
    db_a = sessionmaker(bind=engine_a)()
    cases_a = SyntheticDataGenerator(seed=77).generate_many(db_a, 10)

    engine_b = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine_b)
    db_b = sessionmaker(bind=engine_b)()
    cases_b = SyntheticDataGenerator(seed=77).generate_many(db_b, 10)

    assert [c.matter.title for c in cases_a] == [c.matter.title for c in cases_b]

    db_a.close()
    db_b.close()
    engine_a.dispose()
    engine_b.dispose()


# --- Kollisionsschutz bei reference_number (echter Fund während der Entwicklung) ---


def test_repeated_generation_against_same_db_never_collides_on_reference_number(
    db_session: Session,
) -> None:
    """Regressionstest für einen während der Entwicklung gefundenen Bug:
    `Matter.reference_number` trägt eine UNIQUE-Constraint - ohne
    Kollisionsprüfung hätte eine wiederholte Generator-Nutzung gegen
    dieselbe Datenbank (z. B. mehrere Demo-Sitzungen) irgendwann einen
    harten IntegrityError auslösen können."""
    generator = SyntheticDataGenerator()  # kein Seed -> echte Zufälligkeit
    for _ in range(60):
        generator.generate_case(db_session)

    reference_numbers = [m.reference_number for m in db_session.query(Matter).all()]
    assert len(reference_numbers) == len(set(reference_numbers))


# --- Wissensbasis ---


def test_generate_shared_knowledge_base_creates_approved_entries(
    db_session: Session,
) -> None:
    generator = SyntheticDataGenerator(seed=7)
    sources, knowledge_items = generator.generate_shared_knowledge_base(db_session)

    assert len(sources) > 0
    assert all(s.approval_level == "freigegeben" for s in sources)
    assert len(knowledge_items) > 0
    assert all(k.approval_status == "approved" for k in knowledge_items)


def test_generated_sources_are_indexable_by_existing_search_service(
    db_session: Session,
) -> None:
    """Beweis, dass die generierte Wissensbasis mit der BESTEHENDEN
    Such-/Recherche-Infrastruktur (Prompt 11/14) zusammenspielt, ohne
    Sonderbehandlung - keine Ausnahme wird geworfen."""
    from app.search.service import DocumentSearchService
    from tests.fake_embedding_provider import FakeEmbeddingProvider

    generator = SyntheticDataGenerator(seed=8)
    sources, _ = generator.generate_shared_knowledge_base(db_session)

    search_service = DocumentSearchService(FakeEmbeddingProvider())
    for source in sources:
        search_service.index_source(source, db_session)


# --- Grundregel: nie echte Personen/Domains ---


def test_no_real_looking_domains_used(db_session: Session) -> None:
    generator = SyntheticDataGenerator(seed=9)
    cases = generator.generate_many(db_session, 10)
    for case in cases:
        assert "@example-testdomain.invalid" in case.message.sender
        assert "gmail" not in case.message.sender
        assert "gmx" not in case.message.sender
        assert "web.de" not in case.message.sender
