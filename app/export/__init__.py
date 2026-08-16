"""Strukturierter Aktenexport (Prompt 35).

Siehe service.py: exportiert alle Daten EINER Akte (DSGVO Art. 15/20,
Aktenschließung/Archivierung) als ZIP mit menschenlesbarem JSON-Manifest
+ Original-Dokumentkopien.
"""

from app.export.service import MatterExportService, MatterNotFoundError

__all__ = ["MatterExportService", "MatterNotFoundError"]
