"""Inbox-Endpunkte (Prompt 21).

Zeigt `Message`-Datensaetze - insbesondere auch solche mit `matter_id is
None` (noch keiner Akte zugeordnet, Workflow-Zustand
NEEDS_MATTER_MATCH), damit das Dashboard eine echte "Posteingang"-Ansicht
bauen kann.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import LimitParam, OffsetParam, get_or_404
from app.api.schemas import MessageOut
from app.db.session import get_db
from app.models import Message

router = APIRouter(prefix="/api/inbox", tags=["inbox"])


@router.get("", response_model=list[MessageOut])
def list_inbox_messages(
    db: Session = Depends(get_db),
    matter_id: str | None = Query(
        default=None,
        description="Nur Nachrichten dieser Akte. Weglassen = alle Akten.",
    ),
    unmatched_only: bool = Query(
        default=False,
        description="Nur Nachrichten ohne Aktenzuordnung (matter_id is null).",
    ),
    direction: str | None = Query(
        default=None, description="'inbound' oder 'outbound'."
    ),
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
) -> list[Message]:
    query = db.query(Message)
    if unmatched_only:
        query = query.filter(Message.matter_id.is_(None))
    elif matter_id is not None:
        query = query.filter(Message.matter_id == matter_id)
    if direction is not None:
        query = query.filter(Message.direction == direction)
    return (
        query.order_by(Message.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{message_id}", response_model=MessageOut)
def get_inbox_message(message_id: str, db: Session = Depends(get_db)) -> Message:
    return get_or_404(db, Message, message_id, "Nachricht")
