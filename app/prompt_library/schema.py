"""Eingabe-Validierung für Kanzlei-Prompt-Vorlagen (Schritt 3, Teil 2)."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class PromptTemplateInput(BaseModel):
    name: str
    description: str | None = None
    content: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("name darf nicht leer sein")
        return value

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("content darf nicht leer sein")
        return value
