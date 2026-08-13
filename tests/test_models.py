"""Tests fuer das Datenmodell (Prompt 04).

Nutzt eine eigene In-Memory-SQLite-Datenbank (nicht die konfigurierte
`DATABASE_URL`), damit Tests isoliert und ohne Seiteneffekte auf eine
lokale Datei laufen. `Base.metadata.create_all()` statt Alembic, um Modelle
unabhaengig von Migrationen zu pruefen - die Migration selbst wird separat
manuell verifiziert (upgrade/downgrade, siehe ARCHITECTURE.md).
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    Client,
    Deadline,
    Document,
    Draft,
    KnowledgeItem,
    Matter,
    Message,
    Party,
    Source,
    Task,
    WorkflowRun,
)
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


def test_client_and_matter_can_be_created_with_relationship(
    db_session: Session,
) -> None:
    client = Client(name="Synthetischer Testmandant GmbH")
    matter = Matter(client=client, title="Testakte 1", reference_number="A-0001")
    db_session.add_all([client, matter])
    db_session.commit()

    assert client.id is not None
    assert matter.id is not None
    assert matter.client_id == client.id
    assert matter in client.matters
    # sichere Defaults
    assert matter.status == "open"
    assert client.created_at is not None
    assert client.updated_at is not None


def test_matter_cascades_to_dependent_entities(db_session: Session) -> None:
    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte")
    party = Party(matter=matter, name="Gegenseite GmbH", role="Gegner")
    task = Task(matter=matter, title="Fristprüfung durchführen")
    deadline = Deadline(matter=matter, source_text="Frist laut Schreiben")
    draft = Draft(matter=matter, content="Sehr geehrte Damen und Herren ...")
    workflow_run = WorkflowRun(matter=matter, status="RECEIVED")

    db_session.add_all([client, matter, party, task, deadline, draft, workflow_run])
    db_session.commit()

    assert party in matter.parties
    assert task in matter.tasks
    assert deadline in matter.deadlines
    assert draft in matter.drafts
    assert workflow_run in matter.workflow_runs

    # sichere Defaults fuer sicherheitsrelevante Felder
    assert task.status == "open"
    assert deadline.review_status == "unreviewed"
    assert draft.version == 1
    assert draft.status == "draft"
    assert workflow_run.status == "RECEIVED"


def test_message_and_document_matter_id_nullable_until_matched(
    db_session: Session,
) -> None:
    """Neue Nachrichten/Dokumente duerfen zunaechst unzugeordnet sein
    (Workflow-Zustand NEEDS_MATTER_MATCH), bevor eine Akte feststeht."""
    message = Message(direction="inbound", sender="mandant@example.test")
    document = Document(file_path="/data/intake/testdatei.pdf")

    db_session.add_all([message, document])
    db_session.commit()

    assert message.matter_id is None
    assert document.matter_id is None


def test_document_separates_original_from_extracted_text(
    db_session: Session,
) -> None:
    document = Document(
        file_path="/data/intake/schreiben.pdf",
        original_filename="schreiben.pdf",
        content_hash="abc123",
    )
    db_session.add(document)
    db_session.commit()

    # Original (file_path) ist gesetzt, extrahierter Text (noch) nicht -
    # Trennung Original/Metadaten laut Konzept §7.
    assert document.file_path == "/data/intake/schreiben.pdf"
    assert document.extracted_text is None
    assert document.ocr_status == "not_needed"


def test_source_and_knowledge_item_default_to_unapproved(
    db_session: Session,
) -> None:
    """Rechtsquellen/Kanzleiwissen duerfen nicht automatisch als freigegeben
    gelten (siehe Konzept §5/§6, Prompt 12/14)."""
    source = Source(title="Beispielquelle", source_type="Gesetz")
    knowledge_item = KnowledgeItem(
        title="Beispiel-Kanzleiwissen", content="Interner Textbaustein"
    )
    db_session.add_all([source, knowledge_item])
    db_session.commit()

    assert source.approval_level == "entwurf"
    assert knowledge_item.approval_status == "pending"
    assert knowledge_item.version == 1


def test_matters_of_different_clients_stay_isolated(db_session: Session) -> None:
    """Rudimentärer erster Isolationscheck: Akten unterschiedlicher
    Mandanten duerfen sich nicht im Beziehungsgraph vermischen. Die
    vollstaendige Isolationspruefung (Retrieval, KI-Kontext, Cross-Tenant-
    Zugriffstests) folgt erst in Prompt 41."""
    client_a = Client(name="Mandant A")
    client_b = Client(name="Mandant B")
    matter_a = Matter(client=client_a, title="Akte A")
    matter_b = Matter(client=client_b, title="Akte B")

    db_session.add_all([client_a, client_b, matter_a, matter_b])
    db_session.commit()

    assert matter_a not in client_b.matters
    assert matter_b not in client_a.matters
    assert matter_a.client_id != matter_b.client_id


def test_reference_number_must_be_unique(db_session: Session) -> None:
    client = Client(name="Mandant")
    matter_1 = Matter(client=client, title="Akte 1", reference_number="A-0001")
    matter_2 = Matter(client=client, title="Akte 2", reference_number="A-0001")

    db_session.add_all([client, matter_1, matter_2])
    with pytest.raises(Exception):  # IntegrityError (sqlite3.IntegrityError-Wrapper)
        db_session.commit()
