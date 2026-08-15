"""Postausgang (Prompt 25) – Warteschlange freigegebener Entwürfe mit
manueller Sende-Bestätigung.

GRUNDREGEL (CLAUDE.md, wörtlich): "Keine automatische externe
Kommunikation (insb. E-Mail-Versand) ohne explizite Freigabe." Dieses
Modul hat KEINE Versandfähigkeit - siehe app/models/outbox_entry.py und
app/outbox/service.py für die ausführliche Begründung, analog zur
bestehenden Entscheidung bei app/mail/ (IMAP-Ingestion, strukturell ohne
Sende-Methode).
"""

from app.outbox.service import OutboxEntryAlreadyExistsError, OutboxService

__all__ = ["OutboxService", "OutboxEntryAlreadyExistsError"]
