"""Dokument-Endpunkte (Prompt 21)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import LimitParam, OffsetParam, get_or_404
from app.api.schemas import DocumentOut
from app.db.session import get_db
from app.models import Document

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    matter_id: str | None = Query(default=None),
    classified_type: str | None = Query(default=None),
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
) -> list[Document]:
    query = db.query(Document)
    if matter_id is not None:
        query = query.filter(Document.matter_id == matter_id)
    if classified_type is not None:
        query = query.filter(Document.classified_type == classified_type)
    return (
        query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)) -> Document:
    return get_or_404(db, Document, document_id, "Dokument")
