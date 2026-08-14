"""Feedback des Anwalts zu KI-Entwürfen (Prompt 13).

`DraftFeedbackService` speichert Originalentwurf, Änderungen, Kommentare
und Freigabestatus zu einem `Draft` (Modell aus Prompt 04). WICHTIGSTE
REGEL (Konzept, wörtlich): "Übernehme Änderungen niemals automatisch als
globale Regel." Eine Übernahme in die Kanzlei-Wissensbasis (Prompt 12)
geschieht ausschließlich über den separaten, expliziten Workflow
`promote_to_knowledge` - niemals als Nebeneffekt des Feedback-Speicherns
selbst.
"""

from app.feedback.schema import DraftFeedbackInput
from app.feedback.service import DraftFeedbackService

__all__ = ["DraftFeedbackInput", "DraftFeedbackService"]
