"""Erlaubter Uebergangsgraph fuer die Workflow-State-Machine.

Abgeleitet aus dem End-to-End-Workflow im Konzept (Abschnitt 3: Eingang ->
Quarantaene/Intake -> Extraktion -> Klassifikation -> Aktenzuordnung ->
Kontextaufbau -> Rechtsquellen -> Entwurf -> Qualitaetskontrolle ->
Anwaltliche Freigabe -> Ablage -> Postausgang) sowie ARCHITECTURE.md §6.

Designentscheidungen, die beim Aufstellen des Graphen zu treffen waren
(im Konzept nicht bis ins Detail spezifiziert):
- NEEDS_CLASSIFICATION/NEEDS_MATTER_MATCH sind "Wartezustaende" - nach
  Aufloesung geht es zurueck nach PROCESSING (weitere Schritte folgen)
  oder direkt weiter zu READY_FOR_REVIEW, falls nichts mehr fehlt.
- LEGAL_REVIEW -> DRAFTED ist erlaubt (Konzept: "Zurueckweisen / Neu
  analysieren" in der Entwurfsansicht, Prompt 24) - eine Ablehnung fuehrt
  zurueck zum Entwurfsstadium, nicht zu einem Fehlerzustand.
- APPROVED -> ARCHIVED UND APPROVED -> OUTBOX_READY sind beide erlaubt,
  da Ablage und Postausgang laut Konzept unabhaengige, nicht zwingend
  sequenzielle Schritte nach der Freigabe sind.
- ARCHIVED ist terminal (keine ausgehenden Uebergaenge) - ein archivierter
  Vorgang wird laut Konzept nicht mehr veraendert (vgl. "Rechtsaktualitaet"-
  Prinzip: spaetere Updates ueberschreiben nie die historische Beurteilung).
- ERROR ist von JEDEM nicht-terminalen Zustand aus erreichbar
  (ARCHITECTURE.md §6, woertlich) und kann zurueck nach PROCESSING fuehren
  (einfache Wiederholung - ein vollstaendiges Retry-System folgt erst in
  Prompt 31, hier nur der Zustandsuebergang selbst).
"""

from __future__ import annotations

from app.models.workflow_run import VALID_WORKFLOW_STATUSES

_NON_TERMINAL_STATES = [s for s in VALID_WORKFLOW_STATUSES if s not in ("ARCHIVED",)]

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "RECEIVED": {"PROCESSING", "ERROR"},
    "PROCESSING": {"NEEDS_CLASSIFICATION", "NEEDS_MATTER_MATCH", "READY_FOR_REVIEW", "ERROR"},
    "NEEDS_CLASSIFICATION": {"PROCESSING", "NEEDS_MATTER_MATCH", "READY_FOR_REVIEW", "ERROR"},
    "NEEDS_MATTER_MATCH": {"PROCESSING", "READY_FOR_REVIEW", "ERROR"},
    "READY_FOR_REVIEW": {"DRAFTED", "ERROR"},
    "DRAFTED": {"LEGAL_REVIEW", "ERROR"},
    "LEGAL_REVIEW": {"APPROVED", "DRAFTED", "ERROR"},
    "APPROVED": {"OUTBOX_READY", "ARCHIVED", "ERROR"},
    "OUTBOX_READY": {"ARCHIVED", "ERROR"},
    "ARCHIVED": set(),  # terminal
    "ERROR": {"PROCESSING"},
}

# Absicherung: jeder Zustand aus VALID_WORKFLOW_STATUSES muss einen
# (ggf. leeren) Eintrag im Graphen haben - verhindert stillschweigend
# vergessene Zustaende bei kuenftigen Erweiterungen.
assert set(ALLOWED_TRANSITIONS.keys()) == set(VALID_WORKFLOW_STATUSES), (
    "ALLOWED_TRANSITIONS deckt nicht exakt VALID_WORKFLOW_STATUSES ab"
)
