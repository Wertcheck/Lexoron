"""Tests für app/clients/import_service.py (CSV-/Excel-Massenimport,
Mandantendatenbank, 20.08.)."""

from __future__ import annotations

import io
from collections.abc import Iterator

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients.import_service import (
    ImportFileError,
    import_clients,
    parse_csv,
    parse_xlsx,
)
from app.models import Client
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


def _csv_bytes(text: str) -> bytes:
    return text.encode("utf-8")


# --- parse_csv ---


def test_parse_csv_recognizes_german_headers() -> None:
    content = _csv_bytes(
        "Name,Mandantennummer,Email,Telefon,Rechtsgebiet\r\n"
        "Muster GmbH,M-1,info@muster.test,030 123,Mietrecht\r\n"
    )
    rows = parse_csv(content)
    assert rows == [
        {
            "name": "Muster GmbH",
            "client_number": "M-1",
            "contact_email": "info@muster.test",
            "contact_phone": "030 123",
            "practice_area": "Mietrecht",
        }
    ]


def test_parse_csv_handles_semicolon_delimiter() -> None:
    content = _csv_bytes("Name;Mandantennummer\r\nMuster GmbH;M-2\r\n")
    rows = parse_csv(content)
    assert rows[0]["name"] == "Muster GmbH"
    assert rows[0]["client_number"] == "M-2"


def test_parse_csv_raises_when_required_columns_missing() -> None:
    content = _csv_bytes("Telefon,Email\r\n030 123,info@muster.test\r\n")
    with pytest.raises(ImportFileError):
        parse_csv(content)


def test_parse_csv_raises_on_empty_file() -> None:
    with pytest.raises(ImportFileError):
        parse_csv(b"")


def test_parse_csv_ignores_unknown_columns() -> None:
    content = _csv_bytes(
        "Name,Mandantennummer,Notizen\r\nMuster GmbH,M-3,Vertraulich\r\n"
    )
    rows = parse_csv(content)
    assert "notizen" not in rows[0]
    assert rows[0]["name"] == "Muster GmbH"


# --- parse_xlsx ---


def _build_xlsx(headers: list[str], data_rows: list[list[str]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in data_rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_parse_xlsx_recognizes_headers_and_rows() -> None:
    content = _build_xlsx(
        ["Name", "Mandantennummer", "E-Mail"],
        [["Muster GmbH", "M-10", "info@muster.test"]],
    )
    rows = parse_xlsx(content)
    assert rows == [
        {"name": "Muster GmbH", "client_number": "M-10", "contact_email": "info@muster.test"}
    ]


def test_parse_xlsx_raises_when_required_columns_missing() -> None:
    content = _build_xlsx(["Telefon"], [["030 123"]])
    with pytest.raises(ImportFileError):
        parse_xlsx(content)


def test_parse_xlsx_raises_on_corrupted_file() -> None:
    with pytest.raises(ImportFileError):
        parse_xlsx(b"not a real xlsx file")


# --- import_clients ---


def test_import_clients_creates_valid_rows(db_session: Session) -> None:
    rows = [
        {"name": "Erster Mandant", "client_number": "I-1"},
        {"name": "Zweiter Mandant", "client_number": "I-2"},
    ]
    result = import_clients(db_session, rows, actor="anwalt@kanzlei.test")
    assert result.created_count == 2
    assert result.errors == []
    assert db_session.query(Client).count() == 2


def test_import_clients_skips_row_missing_name_but_keeps_others(db_session: Session) -> None:
    rows = [
        {"name": "", "client_number": "I-10"},
        {"name": "Gueltiger Mandant", "client_number": "I-11"},
    ]
    result = import_clients(db_session, rows, actor="anwalt@kanzlei.test")
    assert result.created_count == 1
    assert result.has_errors
    assert result.errors[0].row_number == 1
    assert db_session.query(Client).filter_by(client_number="I-11").count() == 1


def test_import_clients_skips_row_with_duplicate_client_number_against_existing_db(
    db_session: Session,
) -> None:
    db_session.add(Client(name="Bestehend", client_number="DUP-EXIST", status="active"))
    db_session.commit()

    rows = [{"name": "Neuer Mandant", "client_number": "DUP-EXIST"}]
    result = import_clients(db_session, rows, actor="anwalt@kanzlei.test")
    assert result.created_count == 0
    assert result.has_errors
    assert db_session.query(Client).count() == 1


def test_import_clients_skips_duplicate_within_same_batch(db_session: Session) -> None:
    rows = [
        {"name": "Erster", "client_number": "BATCH-DUP"},
        {"name": "Zweiter (Duplikat)", "client_number": "BATCH-DUP"},
    ]
    result = import_clients(db_session, rows, actor="anwalt@kanzlei.test")
    assert result.created_count == 1
    assert len(result.errors) == 1
    assert db_session.query(Client).filter_by(client_number="BATCH-DUP").count() == 1


def test_import_clients_one_bad_row_does_not_abort_rest_of_batch(db_session: Session) -> None:
    """Kernanforderung: eine fehlerhafte Zeile darf den restlichen Import
    nicht verhindern - siehe app/clients/import_service.py-Moduldocstring
    zur Rollback-Isolation je Zeile."""
    rows = [{"name": "Gut 1", "client_number": f"OK-{i}"} for i in range(5)]
    rows.insert(2, {"name": "", "client_number": "BAD"})
    result = import_clients(db_session, rows, actor="anwalt@kanzlei.test")
    assert result.created_count == 5
    assert len(result.errors) == 1
    assert db_session.query(Client).count() == 5
