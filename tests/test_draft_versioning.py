"""Tests für app/drafting/versioning.py (Prompt 23).

Isolierte Tests für die EINZIGE Stelle im Projekt, die neue Draft-Zeilen
anlegt - hier wird die Kernregel "nie überschreiben, immer neue Zeile"
einmal gründlich geprüft, statt sie in jedem aufrufenden Service erneut
zu verifizieren (die Aufrufer-Tests prüfen nur noch die Integration).
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.drafting.versioning import create_new_draft_version
from app.models import AuditEvent, Client, Draft, Matter
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


def _matter(db: Session) -> Matter:
    client = Client(name="Testmandant")
    matter = Matter(client=client, title="Testakte")
    db.add_all([client, matter])
    db.commit()
    return matter


def test_first_version_has_no_previous_version_and_version_one(
    db_session: Session,
) -> None:
    matter = _matter(db_session)

    draft = create_new_draft_version(
        db_session,
        matter_id=matter.id,
        content="Erster Entwurf",
        actor="system",
        event_type="draft_created",
    )

    assert draft.version == 1
    assert draft.previous_version_id is None
    assert draft.content == "Erster Entwurf"
    assert draft.status == "draft"  # Standardwert


def test_subsequent_version_links_to_previous_and_increments(
    db_session: Session,
) -> None:
    matter = _matter(db_session)
    v1 = create_new_draft_version(
        db_session,
        matter_id=matter.id,
        content="v1",
        actor="system",
        event_type="draft_created",
    )

    v2 = create_new_draft_version(
        db_session,
        matter_id=matter.id,
        content="v2",
        previous_draft=v1,
        actor="anwalt@kanzlei.test",
        event_type="draft_version_created",
    )

    assert v2.version == 2
    assert v2.previous_version_id == v1.id
    assert v2.id != v1.id


def test_creating_new_version_never_mutates_the_previous_row(
    db_session: Session,
) -> None:
    """Kernanforderung: die Vorgaenger-Zeile bleibt nach dem Anlegen einer
    neuen Version in JEDEM Feld unveraendert."""
    matter = _matter(db_session)
    v1 = create_new_draft_version(
        db_session,
        matter_id=matter.id,
        content="Ursprünglicher Inhalt",
        status="legal_review",
        actor="system",
        event_type="draft_created",
    )
    v1_id, v1_content, v1_status, v1_version = v1.id, v1.content, v1.status, v1.version

    create_new_draft_version(
        db_session,
        matter_id=matter.id,
        content="Geänderter Inhalt",
        status="approved",
        previous_draft=v1,
        actor="anwalt@kanzlei.test",
        event_type="draft_version_created",
    )

    # v1 frisch aus der DB laden, um sicherzugehen, dass wirklich nichts
    # persistiert wurde, nicht nur das Python-Objekt unveraendert aussieht.
    db_session.expire_all()
    reloaded_v1 = db_session.get(Draft, v1_id)
    assert reloaded_v1.content == v1_content == "Ursprünglicher Inhalt"
    assert reloaded_v1.status == v1_status == "legal_review"
    assert reloaded_v1.version == v1_version == 1


def test_three_version_chain_is_fully_traceable(db_session: Session) -> None:
    matter = _matter(db_session)
    v1 = create_new_draft_version(
        db_session, matter_id=matter.id, content="v1", actor="system", event_type="draft_created"
    )
    v2 = create_new_draft_version(
        db_session,
        matter_id=matter.id,
        content="v2",
        previous_draft=v1,
        actor="a",
        event_type="draft_version_created",
    )
    v3 = create_new_draft_version(
        db_session,
        matter_id=matter.id,
        content="v3",
        previous_draft=v2,
        actor="a",
        event_type="draft_version_created",
    )

    # Kette rueckwaerts nachvollziehbar.
    assert v3.previous_version_id == v2.id
    assert v2.previous_version_id == v1.id
    assert v1.previous_version_id is None
    assert [v1.version, v2.version, v3.version] == [1, 2, 3]
    assert db_session.query(Draft).count() == 3


def test_message_id_is_inherited_from_previous_draft_when_not_given(
    db_session: Session,
) -> None:
    matter = _matter(db_session)
    v1 = create_new_draft_version(
        db_session,
        matter_id=matter.id,
        content="v1",
        message_id="msg-123",
        actor="system",
        event_type="draft_created",
    )

    v2 = create_new_draft_version(
        db_session,
        matter_id=matter.id,
        content="v2",
        previous_draft=v1,
        actor="a",
        event_type="draft_version_created",
    )

    assert v2.message_id == "msg-123"


def test_each_call_writes_exactly_one_audit_event_with_given_type(
    db_session: Session,
) -> None:
    matter = _matter(db_session)

    draft = create_new_draft_version(
        db_session,
        matter_id=matter.id,
        content="v1",
        actor="system",
        event_type="draft_created",
        details="Testdetail",
    )

    events = db_session.query(AuditEvent).filter_by(entity_id=draft.id).all()
    assert len(events) == 1
    assert events[0].event_type == "draft_created"
    assert events[0].details == "Testdetail"
