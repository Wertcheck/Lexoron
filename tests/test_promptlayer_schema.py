"""Tests fuer app/promptlayer/schema.py (Prompt 16)."""

import pytest
from pydantic import ValidationError

from app.promptlayer.schema import PromptContext, PromptSection


def test_valid_section_is_accepted() -> None:
    section = PromptSection(name="system", content="Regeltext", is_trusted=True)
    assert section.is_trusted is True


def test_unknown_section_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PromptSection(name="irgendwas", content="Text", is_trusted=True)


def test_render_wraps_each_section_in_tags() -> None:
    context = PromptContext(
        matter_id="m1",
        system_rules_version="1",
        sections=[
            PromptSection(name="system", content="Regeltext", is_trusted=True),
            PromptSection(name="fallkontext", content="Aktendaten", is_trusted=False),
        ],
    )

    rendered = context.render()

    assert "<system>" in rendered
    assert "Regeltext" in rendered
    assert "</system>" in rendered
    assert "<fallkontext>" in rendered
    assert "Aktendaten" in rendered


def test_get_section_returns_matching_section() -> None:
    context = PromptContext(
        matter_id="m1",
        system_rules_version="1",
        sections=[PromptSection(name="system", content="Regeltext", is_trusted=True)],
    )

    section = context.get_section("system")

    assert section is not None
    assert section.content == "Regeltext"


def test_get_section_returns_none_when_missing() -> None:
    context = PromptContext(matter_id="m1", system_rules_version="1", sections=[])

    assert context.get_section("system") is None
