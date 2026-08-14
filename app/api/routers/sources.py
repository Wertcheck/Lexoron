"""Rechtsquellen-Endpunkte (Prompt 21)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import LimitParam, OffsetParam, get_or_404
from app.api.schemas import SourceOut
from app.db.session import get_db
from app.models import Source

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(
    db: Session = Depends(get_db),
    source_type: str | None = Query(default=None),
    approval_level: str | None = Query(
        default=None, description="'entwurf', 'freigegeben' oder 'veraltet'."
    ),
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
) -> list[Source]:
    query = db.query(Source)
    if source_type is not None:
        query = query.filter(Source.source_type == source_type)
    if approval_level is not None:
        query = query.filter(Source.approval_level == approval_level)
    return (
        query.order_by(Source.created_at.desc()).offset(offset).limit(limit).all()
    )


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: str, db: Session = Depends(get_db)) -> Source:
    return get_or_404(db, Source, source_id, "Quelle")
