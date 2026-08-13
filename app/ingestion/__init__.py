"""Ingestion – Eingangsverarbeitung (Prompt 05: Scan-Ordner-Überwachung).

Verantwortlich dafür, neue Dateien aus überwachten Ordnern sicher zu
erkennen, zu hashen und in einen kontrollierten Intake-Bereich zu
kopieren, samt Anlage eines `Document`-Metadatensatzes. Enthält bewusst
keine inhaltliche Verarbeitung (Textextraktion, OCR, Klassifikation) -
das entsteht erst in den Prompts 06 und 08.
"""

from app.ingestion.intake import IntakeService
from app.ingestion.watcher import IntakeWatcher

__all__ = ["IntakeService", "IntakeWatcher"]
