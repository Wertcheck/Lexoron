"""Tests für app/laws/service.py (digitale Gesetzesbibliothek, 20.08.)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.laws.service import (
    FIXTURES_DIR,
    LawFixtureError,
    get_law_by_code,
    get_laws,
    get_sections,
    import_all_fixtures,
    import_law_fixture_data,
)
from app.models import Law, LawSection
from app.models.base import Base


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


_SAMPLE_DATA = {
    "code": "TESTG",
    "title": "Testgesetz",
    "sections": [
        {
            "section_number": "§ 1",
            "title": "Erster Paragraph",
            "text_content": "Testinhalt eins.",
            "last_updated": "2026-08-20",
        },
        {
            "section_number": "§ 2",
            "title": "Zweiter Paragraph",
            "text_content": "Testinhalt zwei.",
            "last_updated": "2026-08-20",
        },
    ],
}


# --- import_law_fixture_data ---


def test_import_creates_law_and_sections(db_session: Session) -> None:
    result = import_law_fixture_data(db_session, _SAMPLE_DATA)
    assert result.law_created is True
    assert result.sections_created == 2
    assert result.sections_updated == 0
    assert db_session.query(Law).filter_by(code="TESTG").count() == 1
    assert db_session.query(LawSection).filter_by(law_code="TESTG").count() == 2


def test_import_is_idempotent_upsert(db_session: Session) -> None:
    """Zweimaliger Import derselben Datei darf keine Duplikate erzeugen -
    Kernanforderung fuer den lazy Bootstrap (app/web/laws_router.py) UND
    das wiederholbare Setup-Skript."""
    import_law_fixture_data(db_session, _SAMPLE_DATA)
    second = import_law_fixture_data(db_session, _SAMPLE_DATA)

    assert second.law_created is False
    assert second.sections_created == 0
    assert second.sections_updated == 2
    assert db_session.query(Law).count() == 1
    assert db_session.query(LawSection).count() == 2


def test_import_updates_changed_text_content(db_session: Session) -> None:
    import_law_fixture_data(db_session, _SAMPLE_DATA)
    changed = {
        **_SAMPLE_DATA,
        "sections": [
            {**_SAMPLE_DATA["sections"][0], "text_content": "Geänderter Testinhalt."},
        ],
    }
    import_law_fixture_data(db_session, changed)
    section = db_session.query(LawSection).filter_by(law_code="TESTG", section_number="§ 1").one()
    assert section.text_content == "Geänderter Testinhalt."
    # Der zweite Paragraph aus dem ersten Import bleibt unberührt erhalten.
    assert db_session.query(LawSection).filter_by(law_code="TESTG").count() == 2


@pytest.mark.parametrize(
    "broken_data",
    [
        {"title": "Ohne Code"},
        {"code": "X"},
        {"code": "X", "title": "T", "sections": [{"title": "Ohne Nummer"}]},
    ],
)
def test_import_rejects_missing_required_fields(db_session: Session, broken_data: dict) -> None:
    with pytest.raises(LawFixtureError):
        import_law_fixture_data(db_session, broken_data)
    assert db_session.query(Law).count() == 0


# --- import_all_fixtures (echte mitgelieferte Fixtures) ---


def test_shipped_fixtures_directory_contains_json_files() -> None:
    assert FIXTURES_DIR.is_dir()
    assert list(FIXTURES_DIR.glob("*.json")), "Keine Fixture-Dateien gefunden"


def test_import_all_shipped_fixtures_succeeds(db_session: Session) -> None:
    """Importiert die TATSÄCHLICH mitgelieferten BGB-/StGB-Fixtures - dient
    zugleich als Validierung, dass die JSON-Dateien wohlgeformt sind und
    alle Pflichtfelder enthalten."""
    results = import_all_fixtures(db_session)
    codes = {r.law_code for r in results}
    assert "BGB" in codes
    assert "StGB" in codes
    assert all(r.sections_created > 0 for r in results)

    bgb = get_law_by_code(db_session, "BGB")
    assert bgb is not None
    assert bgb.title == "Bürgerliches Gesetzbuch"
    assert len(get_sections(db_session, "BGB")) >= 3

    stgb_sections = get_sections(db_session, "StGB")
    assert any(s.section_number == "§ 242" for s in stgb_sections)


def test_import_all_fixtures_is_idempotent(db_session: Session) -> None:
    import_all_fixtures(db_session)
    import_all_fixtures(db_session)
    assert db_session.query(Law).count() == 2
    # BGB und StGB haben je 6 kuratierte Paragraphen (siehe fixtures/*.json).
    assert db_session.query(LawSection).count() == 12


# --- sort_sections_naturally ---


def test_sort_sections_naturally_orders_by_number_not_lexically(db_session: Session) -> None:
    import_law_fixture_data(
        db_session,
        {
            "code": "SORT",
            "title": "Sortiertest",
            "sections": [
                {"section_number": "§ 13", "title": "T13", "text_content": "x", "last_updated": "2026-08-20"},
                {"section_number": "§ 2", "title": "T2", "text_content": "x", "last_updated": "2026-08-20"},
                {"section_number": "§ 130", "title": "T130", "text_content": "x", "last_updated": "2026-08-20"},
            ],
        },
    )
    sections = get_sections(db_session, "SORT")
    numbers = [s.section_number for s in sections]
    assert numbers == ["§ 2", "§ 13", "§ 130"]


# --- get_sections (Suche) ---


def test_get_sections_filters_by_search_term(db_session: Session) -> None:
    import_law_fixture_data(db_session, _SAMPLE_DATA)
    results = get_sections(db_session, "TESTG", search="Zweiter")
    assert len(results) == 1
    assert results[0].section_number == "§ 2"


def test_get_sections_search_is_case_insensitive_substring(db_session: Session) -> None:
    import_law_fixture_data(db_session, _SAMPLE_DATA)
    results = get_sections(db_session, "TESTG", search="ERSTER PARAGRAPH")
    assert len(results) == 1
    assert results[0].section_number == "§ 1"

    results = get_sections(db_session, "TESTG", search="nichtvorhandenerbegriff")
    assert results == []

    results = get_sections(db_session, "TESTG", search="paragraph")
    assert len(results) == 2


def test_get_sections_returns_empty_list_for_unknown_law(db_session: Session) -> None:
    assert get_sections(db_session, "UNBEKANNT") == []


def test_get_laws_orders_by_code(db_session: Session) -> None:
    import_law_fixture_data(db_session, {"code": "ZZZ", "title": "Z-Gesetz", "sections": []})
    import_law_fixture_data(db_session, {"code": "AAA", "title": "A-Gesetz", "sections": []})
    laws = get_laws(db_session)
    assert [law.code for law in laws] == ["AAA", "ZZZ"]
