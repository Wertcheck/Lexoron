"""Schema für den strukturierten Prompt-Kontext."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

ALLOWED_SECTION_NAMES = frozenset(
    {"system", "kanzleiregeln", "fallkontext", "rechtsquellen", "nutzeranweisung"}
)


class PromptSection(BaseModel):
    name: str
    content: str
    # False = potenziell nicht-vertrauenswürdiger externer Inhalt
    # (Fallkontext aus Mandantendokumenten, Rechtsquellen-Text). True =
    # von der Kanzlei/dem System kontrollierte Anweisung.
    is_trusted: bool

    @field_validator("name")
    @classmethod
    def name_must_be_known(cls, value: str) -> str:
        if value not in ALLOWED_SECTION_NAMES:
            raise ValueError(
                f"name muss einer von {sorted(ALLOWED_SECTION_NAMES)} sein"
            )
        return value


class PromptContext(BaseModel):
    matter_id: str
    sections: list[PromptSection] = Field(default_factory=list)
    system_rules_version: str
    policy_version: int | None = None

    def render(self) -> str:
        """Baut eine klar durch Tags getrennte Textdarstellung - keine
        Vermischung von Anweisung und Daten. Wird erst in Prompt 17
        tatsächlich an ein Modell übergeben; hier nur die Struktur."""
        parts: list[str] = []
        for section in self.sections:
            parts.append(f"<{section.name}>\n{section.content}\n</{section.name}>")
        return "\n\n".join(parts)

    def get_section(self, name: str) -> PromptSection | None:
        for section in self.sections:
            if section.name == name:
                return section
        return None
