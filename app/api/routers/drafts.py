"""Entwurf-Endpunkte (Prompt 21).

Bewusst nur lesend - Freigabe/Ablehnung/Ueberarbeitung bleiben den
bestehenden Services vorbehalten (DraftFeedbackService,
WorkflowStateMachine), bis eine echte Zugriffskontrolle existiert
(Prompt 26).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import LimitParam, OffsetParam, get_or_404
from app.api.schemas import DraftOut
from app.db.session import get_db
from app.models import Draft

router = APIRouter(prefix="/api/drafts", tags=["drafts"])


@router.get("", response_model=list[DraftOut])
def list_drafts(
    db: Session = Depends(get_db),
    matter_id: str | None = Query(default=None),
    status: str | None = Query(
        default=None, description="z. B. 'draft', 'legal_review', 'approved'."
    ),
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
) -> list[Draft]:
    query = db.query(Draft)
    if matter_id is not None:
        query = query.filter(Draft.matter_id == matter_id)
    if status is not None:
        query = query.filter(Draft.status == status)
    return (
        query.order_by(Draft.created_at.desc()).offset(offset).limit(limit).all()
    )


@router.get("/{draft_id}", response_model=DraftOut)
def get_draft(draft_id: str, db: Session = Depends(get_db)) -> Draft:
    return get_or_404(db, Draft, draft_id, "Entwurf")
