"""WorkflowStateMachine – erzwingt den Uebergangsgraphen aus
transitions.py und protokolliert jeden Uebergang.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditEvent, WorkflowRun
from app.models.workflow_run import VALID_WORKFLOW_STATUSES
from app.workflow.exceptions import InvalidTransitionError
from app.workflow.transitions import ALLOWED_TRANSITIONS


class WorkflowStateMachine:
    def create_workflow_run(
        self,
        db: Session,
        *,
        matter_id: str | None = None,
        document_id: str | None = None,
        message_id: str | None = None,
        actor: str = "system",
    ) -> WorkflowRun:
        workflow_run = WorkflowRun(
            matter_id=matter_id,
            document_id=document_id,
            message_id=message_id,
            status="RECEIVED",
        )
        db.add(workflow_run)
        db.flush()
        db.add(
            AuditEvent(
                entity_type="WorkflowRun",
                entity_id=workflow_run.id,
                event_type="workflow_run_created",
                actor=actor,
                details="Status: RECEIVED",
            )
        )
        db.commit()
        db.refresh(workflow_run)
        return workflow_run

    def transition(
        self,
        workflow_run_id: str,
        new_status: str,
        db: Session,
        *,
        actor: str = "system",
        error_message: str | None = None,
    ) -> WorkflowRun:
        if new_status not in VALID_WORKFLOW_STATUSES:
            raise ValueError(
                f"'{new_status}' ist kein bekannter Workflow-Zustand "
                f"({sorted(VALID_WORKFLOW_STATUSES)})"
            )

        workflow_run = db.query(WorkflowRun).filter_by(id=workflow_run_id).first()
        if workflow_run is None:
            raise ValueError(f"WorkflowRun {workflow_run_id} nicht gefunden")

        current_status = workflow_run.status
        allowed_next = ALLOWED_TRANSITIONS.get(current_status, set())

        if new_status not in allowed_next:
            raise InvalidTransitionError(
                f"Übergang {current_status} -> {new_status} ist nicht erlaubt "
                f"(erlaubt: {sorted(allowed_next) or 'keine (terminal)'})"
            )

        workflow_run.status = new_status
        if new_status == "ERROR" and error_message:
            workflow_run.error_message = error_message

        db.add(
            AuditEvent(
                entity_type="WorkflowRun",
                entity_id=workflow_run.id,
                event_type="workflow_transition",
                actor=actor,
                details=f"{current_status} -> {new_status}",
            )
        )
        db.commit()
        db.refresh(workflow_run)
        return workflow_run
