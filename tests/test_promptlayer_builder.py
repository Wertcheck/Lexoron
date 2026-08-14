"""Tests fuer app/promptlayer/builder.py (Prompt 16).

Schwerpunkt: Aktenisolation - Kontext fuer Akte A darf NIEMALS Daten aus
Akte B enthalten."""

import inspect
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Client, Deadline, Document, Matter, Task
from app.models.base import Base
from app.promptlayer.builder import PromptContextBuilder
from app.promptlayer.policy_service import PolicyService


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


def _matter(db: Session, title: str = "Testakte", **kwargs) -> Matter:
    client = Client(name=f"Mandant für {title}")
    matter = Matter(client=client, title=title, **kwargs)
    db.add_all([client, matter])
    db.commit()
    return matter


def test_build_context_requires_matter_id() -> None:
    builder = PromptContextBuilder()
    with pytest.raises(ValueError):
        builder.build_context("", "Verfasse eine Antwort.", db=None)  # type: ignore[arg-type]


def test_build_context_requires_non_blank_instruction(db_session: Session) -> None:
    matter = _matter(db_session)
    builder = PromptContextBuilder()

    with pytest.raises(ValueError):
        builder.build_context(matter.id, "   ", db_session)


def test_build_context_raises_for_unknown_matter(db_session: Session) -> None:
    builder = PromptContextBuilder()
    with pytest.raises(ValueError):
        builder.build_context("nicht-vorhanden", "Verfasse eine Antwort.", db_session)


def test_build_context_produces_all_five_sections(db_session: Session) -> None:
    matter = _matter(db_session)
    builder = PromptContextBuilder()

    context = builder.build_context(matter.id, "Verfasse eine Antwort.", db_session)

    section_names = {s.name for s in context.sections}
    assert section_names == {
        "system",
        "kanzleiregeln",
        "fallkontext",
        "rechtsquellen",
        "nutzeranweisung",
    }


def test_system_and_nutzeranweisung_sections_are_trusted(db_session: Session) -> None:
    matter = _matter(db_session)
    builder = PromptContextBuilder()

    context = builder.build_context(matter.id, "Verfasse eine Antwort.", db_session)

    assert context.get_section("system").is_trusted is True
    assert context.get_section("nutzeranweisung").is_trusted is True


def test_fallkontext_and_rechtsquellen_sections_are_untrusted(
    db_session: Session,
) -> None:
    matter = _matter(db_session)
    builder = PromptContextBuilder()

    context = builder.build_context(matter.id, "Verfasse eine Antwort.", db_session)

    assert context.get_section("fallkontext").is_trusted is False
    assert context.get_section("rechtsquellen").is_trusted is False


def test_fallkontext_never_contains_data_from_other_matter(
    db_session: Session,
) -> None:
    """Kernanforderung: keine Mandantendaten aus einer anderen Akte im
    Kontext."""
    matter_a = _matter(db_session, title="Akte A - Mandant Müller")
    matter_b = _matter(db_session, title="Akte B - Mandant Schmidt")

    doc_a = Document(
        file_path="/tmp/a.pdf",
        matter_id=matter_a.id,
        extracted_text="Streng vertraulicher Inhalt von Mandant Müller",
    )
    doc_b = Document(
        file_path="/tmp/b.pdf",
        matter_id=matter_b.id,
        extracted_text="Streng vertraulicher Inhalt von Mandant Schmidt",
    )
    db_session.add_all([doc_a, doc_b])
    db_session.commit()

    builder = PromptContextBuilder()
    context = builder.build_context(matter_a.id, "Verfasse eine Antwort.", db_session)

    fallkontext_text = context.get_section("fallkontext").content
    assert "Müller" in fallkontext_text
    assert "Schmidt" not in fallkontext_text
    assert "Mandant Schmidt" not in fallkontext_text


def test_fallkontext_includes_deadlines_and_open_tasks(db_session: Session) -> None:
    matter = _matter(db_session)
    deadline = Deadline(
        matter=matter, source_text="Frist laut Bescheid", confidence=0.4
    )
    task = Task(matter=matter, title="Fristprüfung durchführen", status="open")
    db_session.add_all([deadline, task])
    db_session.commit()

    builder = PromptContextBuilder()
    context = builder.build_context(matter.id, "Verfasse eine Antwort.", db_session)

    fallkontext_text = context.get_section("fallkontext").content
    assert "Frist laut Bescheid" in fallkontext_text
    assert "Fristprüfung durchführen" in fallkontext_text


def test_uses_active_policy_content(db_session: Session) -> None:
    matter = _matter(db_session)
    policy_service = PolicyService()
    policy_service.create_version(
        "default", "Nutze stets die Sie-Anrede.", db_session, actor="system"
    )

    builder = PromptContextBuilder(policy_service)
    context = builder.build_context(matter.id, "Verfasse eine Antwort.", db_session)

    assert "Sie-Anrede" in context.get_section("kanzleiregeln").content
    assert context.policy_version == 1


def test_missing_policy_uses_placeholder_without_crashing(db_session: Session) -> None:
    matter = _matter(db_session)
    builder = PromptContextBuilder()

    context = builder.build_context(matter.id, "Verfasse eine Antwort.", db_session)

    assert context.get_section("kanzleiregeln").content
    assert context.policy_version is None


def test_render_never_mixes_sections_without_separation(db_session: Session) -> None:
    matter = _matter(db_session)
    builder = PromptContextBuilder()

    context = builder.build_context(matter.id, "Verfasse eine Antwort.", db_session)
    rendered = context.render()

    # Jede Sektion muss als eigener, klar abgegrenzter Block erscheinen.
    for name in ["system", "kanzleiregeln", "fallkontext", "rechtsquellen", "nutzeranweisung"]:
        assert f"<{name}>" in rendered
        assert f"</{name}>" in rendered


def test_build_context_signature_requires_matter_id() -> None:
    """Architektonischer Schutztest, analog zu Prompt 11/15: build_context
    darf strukturell nicht ohne matter_id aufrufbar sein."""
    signature = inspect.signature(PromptContextBuilder.build_context)
    assert "matter_id" in signature.parameters
