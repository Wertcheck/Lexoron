"""Tests fuer app/search/schema.py (Prompt 11)."""

import pytest
from pydantic import ValidationError

from app.search.schema import SearchResult


def test_valid_result_is_accepted() -> None:
    result = SearchResult(
        entity_type="Document",
        entity_id="abc",
        snippet="Ein Ausschnitt",
        score=0.8,
        match_type="fulltext",
    )
    assert result.entity_type == "Document"


def test_unknown_entity_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchResult(
            entity_type="Matter",  # nicht erlaubt - keine direkte Aktensuche
            entity_id="abc",
            snippet="Text",
            score=0.5,
            match_type="fulltext",
        )


def test_unknown_match_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchResult(
            entity_type="Document",
            entity_id="abc",
            snippet="Text",
            score=0.5,
            match_type="irgendwas",
        )


def test_blank_snippet_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchResult(
            entity_type="Document",
            entity_id="abc",
            snippet="   ",
            score=0.5,
            match_type="fulltext",
        )


def test_score_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchResult(
            entity_type="Document",
            entity_id="abc",
            snippet="Text",
            score=1.5,
            match_type="fulltext",
        )
