"""Tests für app/pilot_feedback/service.py (Schritt 3)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import AuditEvent, PilotFeedback
from app.models.base import Base
from app.pilot_feedback.schema import PilotFeedbackInput
from app.pilot_feedback.service import PilotFeedbackService


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


def test_submit_stores_entry_with_ai_classification(db_session: Session) -> None:
    data = PilotFeedbackInput(category="fehler", message="Die App stürzt ab, Fehlermeldung X.")
    entry = PilotFeedbackService().submit(db_session, data, actor="mitarbeiter@kanzlei.test")

    assert entry.id is not None
    assert entry.category == "fehler"
    assert entry.ai_suggested_category == "fehler"
    assert entry.review_status == "neu"
    assert entry.requires_admin_review is False


def test_submit_flags_system_change_suggestions_for_admin_review(db_session: Session) -> None:
    data = PilotFeedbackInput(
        category="verbesserungsvorschlag",
        message="Die KI soll das Prompt anpassen und weniger förmlich formulieren.",
    )
    entry = PilotFeedbackService().submit(db_session, data, actor="anwalt@kanzlei.test")

    assert entry.requires_admin_review is True
    assert entry.review_status == "zur_pruefung"


def test_submit_never_stores_raw_processing_error_messages(db_session: Session) -> None:
    """system_context_json darf NUR Zaehlwerte/Ja-Nein-Status enthalten,
    niemals die eigentliche technische Fehlermeldung eines
    ProcessingError-Eintrags (siehe Modul-Docstring)."""
    from app.models import Client, Document, Matter

    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte")
    document = Document(matter=matter, original_filename="scan.pdf", file_path="/data/scan.pdf")
    db_session.add_all([client, matter, document])
    db_session.commit()

    from app.errors import RetryService

    RetryService().record_failure(
        db_session,
        entity_type="Document",
        entity_id=document.id,
        operation="ocr",
        error_category="transient",
        error_message="GEHEIME_TECHNISCHE_DETAILMELDUNG_XYZ",
    )

    data = PilotFeedbackInput(category="fehler", message="OCR scheint nicht zu laufen.")
    entry = PilotFeedbackService().submit(db_session, data, actor="mitarbeiter@kanzlei.test")

    assert "GEHEIME_TECHNISCHE_DETAILMELDUNG_XYZ" not in (entry.system_context_json or "")
    assert '"pending_processing_errors": 1' in entry.system_context_json


def test_submit_creates_audit_event(db_session: Session) -> None:
    data = PilotFeedbackInput(category="frage", message="Wie funktioniert die Fristenerkennung?")
    entry = PilotFeedbackService().submit(db_session, data, actor="anwalt@kanzlei.test")

    audit = (
        db_session.query(AuditEvent)
        .filter_by(entity_type="PilotFeedback", entity_id=entry.id)
        .first()
    )
    assert audit is not None
    assert audit.event_type == "pilot_feedback_submitted"


def test_review_approves_entry_and_records_actor(db_session: Session) -> None:
    data = PilotFeedbackInput(category="verbesserungsvorschlag", message="Prompt anpassen bitte.")
    entry = PilotFeedbackService().submit(db_session, data, actor="mitarbeiter@kanzlei.test")
    assert entry.review_status == "zur_pruefung"

    reviewed = PilotFeedbackService().review(
        db_session, entry, action="freigegeben", actor="admin@kanzlei.test", comment="OK, wird umgesetzt."
    )

    assert reviewed.review_status == "freigegeben"
    assert reviewed.reviewed_by_actor == "admin@kanzlei.test"
    assert reviewed.review_comment == "OK, wird umgesetzt."


def test_review_rejects_unknown_action(db_session: Session) -> None:
    data = PilotFeedbackInput(category="fehler", message="Etwas ist kaputt.")
    entry = PilotFeedbackService().submit(db_session, data, actor="mitarbeiter@kanzlei.test")

    with pytest.raises(ValueError):
        PilotFeedbackService().review(db_session, entry, action="gelöscht", actor="admin@kanzlei.test")


def test_list_pending_review_only_returns_flagged_entries(db_session: Session) -> None:
    service = PilotFeedbackService()
    service.submit(
        db_session,
        PilotFeedbackInput(category="lob", message="Toll gemacht!"),
        actor="a@kanzlei.test",
    )
    flagged = service.submit(
        db_session,
        PilotFeedbackInput(category="verbesserungsvorschlag", message="Systemregel anpassen bitte."),
        actor="b@kanzlei.test",
    )

    pending = service.list_pending_review(db_session)

    assert [entry.id for entry in pending] == [flagged.id]
