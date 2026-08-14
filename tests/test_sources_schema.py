"""Tests fuer app/sources/schema.py (Prompt 14)."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.sources.schema import SourceImport


def test_valid_import_is_accepted() -> None:
    source = SourceImport(title="§ 370 AO", source_type="Gesetz")
    assert source.reference is None


def test_blank_title_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceImport(title="   ", source_type="Gesetz")


def test_unknown_source_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceImport(title="Titel", source_type="Irgendwas Erfundenes")


def test_verwaltungsanweisung_is_a_valid_source_type() -> None:
    """Wichtig fuer eine Steuerkanzlei: BMF-Schreiben etc."""
    source = SourceImport(title="BMF-Schreiben vom 01.01.2027", source_type="Verwaltungsanweisung")
    assert source.source_type == "Verwaltungsanweisung"


def test_valid_from_after_valid_until_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceImport(
            title="Titel",
            source_type="Gesetz",
            valid_from=date(2027, 6, 1),
            valid_until=date(2027, 1, 1),
        )
