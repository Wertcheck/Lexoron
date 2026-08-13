"""Tests fuer app/knowledge/schema.py (Prompt 12)."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.knowledge.schema import KnowledgeItemImport


def test_valid_import_is_accepted() -> None:
    item = KnowledgeItemImport(title="Testbaustein", content="Testinhalt")
    assert item.category is None


def test_blank_title_is_rejected() -> None:
    with pytest.raises(ValidationError):
        KnowledgeItemImport(title="   ", content="Testinhalt")


def test_blank_content_is_rejected() -> None:
    with pytest.raises(ValidationError):
        KnowledgeItemImport(title="Titel", content="")


def test_valid_from_after_valid_until_is_rejected() -> None:
    with pytest.raises(ValidationError):
        KnowledgeItemImport(
            title="Titel",
            content="Inhalt",
            valid_from=date(2027, 6, 1),
            valid_until=date(2027, 1, 1),
        )


def test_equal_valid_from_and_valid_until_is_accepted() -> None:
    item = KnowledgeItemImport(
        title="Titel",
        content="Inhalt",
        valid_from=date(2027, 1, 1),
        valid_until=date(2027, 1, 1),
    )
    assert item.valid_from == item.valid_until
