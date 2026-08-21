"""Eingabe-Validierung für Dokumentvorlagen (Block 3, 20.08.)."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class DocumentTemplateInput(BaseModel):
    name: str
    category: str | None = None
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
