"""Tests fuer app/mail/service.py (Prompt 07).

Nutzt einen Fake-Provider (erfuellt nur MailProvider.fetch_new_messages),
kein echter IMAP-Server. Genau das ist der Zweck der Provider-Abstraktion:
der Service laesst sich unabhaengig von einer echten Mailbox testen.
"""

from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.mail.base import FetchedAttachment, FetchedMessage
from app.mail.service import MailIngestionService
from app.models import AuditEvent, Document, Message
from app.models.base import Base


class FakeMailProvider:
    """Erfuellt MailProvider strukturell (Protocol), ohne von ihm zu erben."""

    def __init__(self, messages: list[FetchedMessage]) -> None:
        self._messages = messages

    def fetch_new_messages(self) -> list[FetchedMessage]:
        return self._messages


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


def _synthetic_message(**overrides) -> FetchedMessage:
    defaults = dict(
        external_message_id="<synthetisch@example.test>",
        sender="mandant@example.test",
        recipient="kanzlei@example.test",
        subject="Testbetreff",
        body_text="Synthetischer Testinhalt.",
        received_at=datetime.now(timezone.utc),
        attachments=[],
    )
    defaults.update(overrides)
    return FetchedMessage(**defaults)


def test_ingest_creates_message_record(tmp_path, db_session: Session) -> None:
    provider = FakeMailProvider([_synthetic_message()])
    service = MailIngestionService(provider, tmp_path / "attachments")

    created = service.ingest_new_messages(db_session)

    assert len(created) == 1
    message = created[0]
    assert message.sender == "mandant@example.test"
    assert message.subject == "Testbetreff"
    assert message.direction == "inbound"
    assert message.matter_id is None  # Aktenzuordnung folgt erst Prompt 09


def test_ingest_stores_attachments_as_separate_documents(
    tmp_path, db_session: Session
) -> None:
    attachment = FetchedAttachment(
        filename="schreiben.pdf",
        content=b"Synthetischer Anhangsinhalt",
        mime_type="application/pdf",
    )
    provider = FakeMailProvider([_synthetic_message(attachments=[attachment])])
    storage_dir = tmp_path / "attachments"
    service = MailIngestionService(provider, storage_dir)

    created = service.ingest_new_messages(db_session)
    message = created[0]

    documents = db_session.query(Document).filter_by(message_id=message.id).all()
    assert len(documents) == 1
    document = documents[0]
    assert document.original_filename == "schreiben.pdf"
    assert document.mime_type == "application/pdf"

    from pathlib import Path

    stored_path = Path(document.file_path)
    assert stored_path.exists()
    assert stored_path.parent == storage_dir
    assert stored_path.read_bytes() == b"Synthetischer Anhangsinhalt"


def test_ingest_deduplicates_by_external_message_id(
    tmp_path, db_session: Session
) -> None:
    """Dieselbe Nachricht darf nicht zweimal als Message-Datensatz
    landen, selbst wenn der Provider sie erneut liefert."""
    same_message = _synthetic_message(external_message_id="<dupe@example.test>")
    provider = FakeMailProvider([same_message])
    service = MailIngestionService(provider, tmp_path / "attachments")

    first_run = service.ingest_new_messages(db_session)
    assert len(first_run) == 1

    second_run = service.ingest_new_messages(db_session)
    assert len(second_run) == 0
    assert db_session.query(Message).count() == 1


def test_ingest_creates_audit_event(tmp_path, db_session: Session) -> None:
    provider = FakeMailProvider([_synthetic_message()])
    service = MailIngestionService(provider, tmp_path / "attachments")

    created = service.ingest_new_messages(db_session)
    message = created[0]

    events = db_session.query(AuditEvent).filter_by(entity_id=message.id).all()
    assert len(events) == 1
    assert events[0].entity_type == "Message"
    assert events[0].event_type == "mail_ingested"


def test_ingest_multiple_distinct_messages(tmp_path, db_session: Session) -> None:
    provider = FakeMailProvider(
        [
            _synthetic_message(external_message_id="<eins@example.test>"),
            _synthetic_message(external_message_id="<zwei@example.test>"),
        ]
    )
    service = MailIngestionService(provider, tmp_path / "attachments")

    created = service.ingest_new_messages(db_session)

    assert len(created) == 2
    assert db_session.query(Message).count() == 2


def test_mail_provider_has_no_send_capability() -> None:
    """Architektonischer Schutz: MailProvider darf strukturell keine
    Sende-Methode anbieten (siehe app/mail/base.py Docstring)."""
    from app.mail.base import MailProvider

    protocol_methods = [
        name for name in dir(MailProvider) if not name.startswith("_")
    ]
    assert protocol_methods == ["fetch_new_messages"]
