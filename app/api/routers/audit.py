"""Audit-Endpunkte (Prompt 21).

Nutzt ausschliesslich den bestehenden `AuditLogService` (Prompt 19) -
keine eigene Query-Logik hier, um die Aktenisolations-Garantie dieses
Service (siehe app/audit/service.py) nicht zu duplizieren oder versehentlich
abzuschwaechen.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import AuditEventOut
from app.audit.service import AuditLogService
from app.db.session import get_db
from app.models import AuditEvent

router = APIRouter(prefix="/api/audit", tags=["audit"])

_service = AuditLogService()


@router.get("/matter/{matter_id}", response_model=list[AuditEventOut])
def list_audit_events_for_matter(
    matter_id: str, db: Session = Depends(get_db)
) -> list[AuditEvent]:
    return _service.list_events_for_matter(matter_id, db)


@router.get("/entity/{entity_type}/{entity_id}", response_model=list[AuditEventOut])
def list_audit_events_for_entity(
    entity_type: str, entity_id: str, db: Session = Depends(get_db)
) -> list[AuditEvent]:
    return _service.list_events_for_entity(entity_type, entity_id, db)
