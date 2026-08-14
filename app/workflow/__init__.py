"""Workflow-State-Machine (Prompt 20).

`WorkflowRun` existiert als Modell bereits seit Prompt 04 (inkl. der in
ARCHITECTURE.md §6 festgelegten Zustandsliste), wurde bislang aber von
keinem Service tatsaechlich verwendet. Dieses Modul liefert die fehlende
Logik nach: ein fester Uebergangsgraph (`ALLOWED_TRANSITIONS`) und ein
Service, der JEDEN Uebergang dagegen prueft und protokolliert.

Zustaende (unveraendert aus ARCHITECTURE.md §6):
RECEIVED, PROCESSING, NEEDS_CLASSIFICATION, NEEDS_MATTER_MATCH,
READY_FOR_REVIEW, DRAFTED, LEGAL_REVIEW, APPROVED, ARCHIVED,
OUTBOX_READY, ERROR (von jedem nicht-terminalen Zustand aus erreichbar).

Nur definierte Uebergaenge sind erlaubt - ein Versuch, einen nicht in
`ALLOWED_TRANSITIONS` gelisteten Uebergang durchzufuehren, wirft
`InvalidTransitionError` und aendert NICHTS am Datensatz.
"""

from app.workflow.exceptions import InvalidTransitionError
from app.workflow.service import WorkflowStateMachine
from app.workflow.transitions import ALLOWED_TRANSITIONS

__all__ = ["WorkflowStateMachine", "InvalidTransitionError", "ALLOWED_TRANSITIONS"]
