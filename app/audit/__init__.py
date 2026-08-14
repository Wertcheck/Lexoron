"""Audit-Log-Abfrageschicht (Prompt 19).

`AuditEvent` selbst existiert bereits seit Prompt 04 und wird seither von
praktisch jedem Modul beim Erzeugen/Aendern relevanter Datensaetze
mitgeschrieben (Intake, Klassifikation, Aktenzuordnung, Fristenanalyse,
Wissensbasis, Rechtsquellen, Feedback, Policies, Drafting, Review,
API-Aufrufe). Prompt 19 ergaenzt:

1. Technische append-only-Durchsetzung (siehe app/models/audit_event.py:
   `AuditLogImmutableError` bei Aenderungs-/Loeschversuchen).
2. Automatische Laengenbegrenzung von `details` (technischer Rueckhalt
   gegen versehentliche grosse/sensible Inhalte im Log).
3. `AuditLogService` - lesende Abfrage des bereits vorhandenen Logs,
   insbesondere aktenweise (fuer die spaetere Aktenansicht, Prompt 23).

Siehe ARCHITECTURE.md fuer eine vollstaendige Uebersicht, welche der vom
Konzept geforderten Kategorien (Intake, Klassifikation, Zuordnung,
Recherche, Entwurf, Aenderungen, Freigaben, Ablage) bereits durch
bestehende AuditEvents abgedeckt sind.
"""

from app.audit.service import AuditLogService

__all__ = ["AuditLogService"]
