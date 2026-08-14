"""Tests fuer app/sources/service.py (Prompt 14)."""

from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import AuditEvent, Source
from app.models.base import Base
from app.sources.schema import SourceImport
from app.sources.service import SourceService


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


def test_import_creates_draft_source_with_manual_provider(db_session: Session) -> None:
    service = SourceService()
    data = SourceImport(title="§ 370 AO", source_type="Gesetz", reference="AO § 370")

    source = service.import_source(data, db_session, actor="anwalt@kanzlei.test")

    assert source.approval_level == "entwurf"
    assert source.provider_name == "manual"
    assert source.retrieved_at == date.today()


def test_import_creates_audit_event(db_session: Session) -> None:
    service = SourceService()
    data = SourceImport(title="Titel", source_type="Gesetz")

    source = service.import_source(data, db_session, actor="anwalt@kanzlei.test")

    events = db_session.query(AuditEvent).filter_by(entity_id=source.id).all()
    assert len(events) == 1
    assert events[0].event_type == "source_imported"


def test_approve_source_sets_status_and_logs(db_session: Session) -> None:
    service = SourceService()
    source = service.import_source(
        SourceImport(title="Titel", source_type="Gesetz"), db_session, actor="system"
    )

    approved = service.approve_source(source, db_session, actor="anwalt@kanzlei.test")

    assert approved.approval_level == "freigegeben"
    events = db_session.query(AuditEvent).filter_by(
        entity_id=source.id, event_type="source_approved"
    ).all()
    assert len(events) == 1


def test_mark_outdated_requires_reason(db_session: Session) -> None:
    service = SourceService()
    source = service.import_source(
        SourceImport(title="Titel", source_type="Gesetz"), db_session, actor="system"
    )
    service.approve_source(source, db_session, actor="system")

    with pytest.raises(ValueError):
        service.mark_outdated(source, db_session, actor="system", reason="   ")


def test_mark_outdated_sets_status_and_logs_reason(db_session: Session) -> None:
    service = SourceService()
    source = service.import_source(
        SourceImport(title="Titel", source_type="Gesetz"), db_session, actor="system"
    )
    service.approve_source(source, db_session, actor="system")

    outdated = service.mark_outdated(
        source, db_session, actor="anwalt@kanzlei.test", reason="Durch Gesetzesänderung überholt"
    )

    assert outdated.approval_level == "veraltet"
    events = db_session.query(AuditEvent).filter_by(
        entity_id=source.id, event_type="source_marked_outdated"
    ).all()
    assert events[0].details == "Durch Gesetzesänderung überholt"


def test_source_remains_in_database_after_marked_outdated(db_session: Session) -> None:
    """Historische Nachvollziehbarkeit: eine veraltete Quelle wird nicht
    geloescht (siehe ARCHITECTURE.md Rechtsaktualitaet)."""
    service = SourceService()
    source = service.import_source(
        SourceImport(title="Titel", source_type="Gesetz"), db_session, actor="system"
    )
    service.mark_outdated(source, db_session, actor="system", reason="Überholt")

    assert db_session.query(Source).count() == 1


def test_list_sources_filters_by_type_and_approval_level(db_session: Session) -> None:
    service = SourceService()
    law = service.import_source(
        SourceImport(title="§ 370 AO", source_type="Gesetz"), db_session, actor="system"
    )
    service.import_source(
        SourceImport(title="BFH-Urteil", source_type="Rechtsprechung"),
        db_session,
        actor="system",
    )
    service.approve_source(law, db_session, actor="system")

    results = service.list_sources(
        db_session, source_type="Gesetz", approval_level="freigegeben"
    )

    assert len(results) == 1
    assert results[0].id == law.id


def test_list_sources_only_currently_valid_excludes_expired(db_session: Session) -> None:
    service = SourceService()
    expired = service.import_source(
        SourceImport(
            title="Abgelaufene Verwaltungsanweisung",
            source_type="Verwaltungsanweisung",
            valid_until=date.today() - timedelta(days=1),
        ),
        db_session,
        actor="system",
    )
    current = service.import_source(
        SourceImport(title="Aktuelles Gesetz", source_type="Gesetz"),
        db_session,
        actor="system",
    )

    results = service.list_sources(db_session, only_currently_valid=True)
    result_ids = {r.id for r in results}

    assert current.id in result_ids
    assert expired.id not in result_ids
