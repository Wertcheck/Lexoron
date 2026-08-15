"""Schema für app/attorney_instructions/service.py."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, field_validator

from app.drafting.schema import DraftingResult
from app.models import AttorneyInstruction, Draft


class AttorneyInstructionInput(BaseModel):
    instruction_text: str

    @field_validator("instruction_text")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("instruction_text darf nicht leer sein")
        return value


@dataclass
class ApplyInstructionResult:
    """Rückgabe von `AttorneyInstructionService.apply_instruction`.

    `drafting_result.success=False` (z. B. vom Privacy Gateway blockiert
    oder Fehler bei der Textproduktion) bedeutet: KEINE neue Draft-Version
    entstanden, die `AttorneyInstruction` bleibt bewusst im Status "open"
    (siehe Service) - ein gescheiterter Versuch darf nicht fälschlich als
    "applied" markiert werden.
    """

    instruction: AttorneyInstruction
    drafting_result: DraftingResult
    new_draft: Draft | None = None
