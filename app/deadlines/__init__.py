"""Fristen-/Aufgabenanalyse (Prompt 10).

Extrahiert mögliche Fristen und Termine aus Dokumenttext. WICHTIG (Konzept
Prompt 10, wörtlich): "Er darf aus Dokumenten mögliche Fristen, Termine und
Handlungen extrahieren, aber keine Frist endgültig als verbindlich
markieren." Jede erkannte Frist erhält daher immer `review_status =
"unreviewed"` (Default aus dem Deadline-Modell, Prompt 04) - dieser
Service setzt diesen Status NIE auf "confirmed".

Wie bei Klassifikation (Prompt 08) und Aktenzuordnung (Prompt 09) bewusst
noch ohne LLM: `PlaceholderDeadlineExtractor` nutzt Datums-/Keyword-
Heuristiken. Eine Frist kann nur einer Akte zugeordnet werden, wenn das
Dokument bereits einer Akte zugeordnet ist (Prompt 09) - `Deadline.matter_id`
ist nicht nullable.
"""

from app.deadlines.extractor import DeadlineExtractor, PlaceholderDeadlineExtractor
from app.deadlines.schema import ExtractedDeadline
from app.deadlines.service import DeadlineAnalysisService

__all__ = [
    "DeadlineExtractor",
    "PlaceholderDeadlineExtractor",
    "ExtractedDeadline",
    "DeadlineAnalysisService",
]
