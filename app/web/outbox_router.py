"""Dashboard-Router für den Postausgang (Prompt 25).

GRUNDREGEL (CLAUDE.md, wörtlich): "Keine automatische externe
Kommunikation (insb. E-Mail-Versand) ohne explizite Freigabe." Dieser
Router hat KEINE Versandfähigkeit - siehe app/outbox/service.py.
`mark_sent` bestätigt nur eine manuelle, bereits AUSSERHALB des Systems
erfolgte Handlung.

Getrennt von app/web/drafts_router.py gehalten (eigene, klar abgegrenzte
Zuständigkeit), analog zur bestehenden Modultrennung (Inbox/Drafts/Outbox
je eigener Router).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_or_404
from app.db.session import get_db
from app.models import Draft, OutboxEntry
from app.outbox.service import OutboxService

router = APIRouter(prefix="/dashboard/outbox", tags=["dashboard-outbox"])

templates = Jinja2Templates(directory="app/web/templates")


@router.get("", response_class=HTMLResponse)
def outbox_list_page(
    request: Request,
    status: str = "pending",
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    query = db.query(OutboxEntry).options(
        joinedload(OutboxEntry.draft).joinedload(Draft.matter)
    )
    if status in ("pending", "sent"):
        query = query.filter(OutboxEntry.status == status)
    entries = query.order_by(OutboxEntry.created_at.desc()).all()

    context = {
        "request": request,
        "active_nav": "Postausgang",
        "entries": entries,
        "active_status": status,
        "error": error,
    }
    return templates.TemplateResponse(request, "outbox_list.html", context)


@router.post("/{entry_id}/mark-sent")
def mark_sent(
    entry_id: str,
    actor: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Bestätigt manuell, dass der Anwalt bereits (außerhalb dieses
    Systems) versendet hat. Löst selbst nichts aus."""
    entry = get_or_404(db, OutboxEntry, entry_id, "Postausgang-Eintrag")
    try:
        OutboxService().mark_as_sent(entry, db, actor=actor.strip())
    except ValueError as exc:
        # Z. B. Doppelklick oder zwei parallel geöffnete Tabs - bereits
        # als versendet markiert. Sauberer Hinweis statt Serverfehler.
        return RedirectResponse(url=f"/dashboard/outbox?error={exc}", status_code=303)
    return RedirectResponse(url="/dashboard/outbox", status_code=303)
