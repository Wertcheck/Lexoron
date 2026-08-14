"""Kanzlei-Wissen-Endpunkte (Prompt 21).

Bewusst nur lesend. Die Freigabe (`approval_status`) und die Uebernahme
aus Feedback bleiben eigene, explizite Workflows (KnowledgeService,
DraftFeedbackService.promote_to_knowledge) - siehe Grundregel in
app/models/knowledge_item.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import LimitParam, OffsetParam, get_or_404
from app.api.schemas import KnowledgeItemOut
from app.db.session import get_db
from app.models import KnowledgeItem

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeItemOut])
def list_knowledge_items(
    db: Session = Depends(get_db),
    approval_status: str | None = Query(
        default=None, description="'pending', 'approved' oder 'deactivated'."
    ),
    category: str | None = Query(default=None),
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
) -> list[KnowledgeItem]:
    query = db.query(KnowledgeItem)
    if approval_status is not None:
        query = query.filter(KnowledgeItem.approval_status == approval_status)
    if category is not None:
        query = query.filter(KnowledgeItem.category == category)
    return (
        query.order_by(KnowledgeItem.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{knowledge_item_id}", response_model=KnowledgeItemOut)
def get_knowledge_item(
    knowledge_item_id: str, db: Session = Depends(get_db)
) -> KnowledgeItem:
    return get_or_404(db, KnowledgeItem, knowledge_item_id, "Wissenselement")
