"""AttorneyInstruction – konkrete Änderungs-/Arbeitsaufträge des Anwalts an
die nächste Entwurfsversion (Prompt 23).

Bewusst getrennt von `app/feedback/` (DraftFeedback = anwaltliche
Bewertung/Position zu einem VORLIEGENDEN Entwurf) - siehe
app/models/attorney_instruction.py für die vollständige Abgrenzung.
"""

from app.attorney_instructions.service import AttorneyInstructionService

__all__ = ["AttorneyInstructionService"]
