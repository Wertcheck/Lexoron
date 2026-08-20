"""Dashboard-Router für "Pilot-Feedback & Support" (Schritt 3, 20.08.).

Abgabe des Formulars: alle drei Rollen (kein besonderes Kostenrisiko, kein
Claude-API-Aufruf - siehe app/pilot_feedback/classifier.py). Die
Admin-Freigabe-Schleife für Einträge, die auf eine System-/Prompt-Änderung
hindeuten (`requires_admin_review`), ist dagegen ausschließlich Admins
vorbehalten - konsistent mit der Rechte-Matrix (app/auth/permissions.py),
die eine solche Aktion keiner der drei Standardrollen explizit zuweist."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_or_404
from app.auth.permissions import require_login, require_role
from app.db.session import get_db
from app.models import PilotFeedback, User
from app.pilot_feedback.schema import PilotFeedbackInput
from app.pilot_feedback.service import PilotFeedbackService
from app.web.template_paths import TEMPLATES_DIR

router = APIRouter(prefix="/dashboard/feedback", tags=["dashboard-feedback"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("", response_class=HTMLResponse)
def feedback_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
) -> HTMLResponse:
    is_admin = bool(
        current_user.role and current_user.role.name.strip().lower() == "admin"
    )
    service = PilotFeedbackService()
    context = {
        "request": request,
        "active_nav": "Pilot-Feedback & Support",
        "current_user": current_user,
        "is_admin": is_admin,
        "entries": service.list_all(db),
        "csrf_token": getattr(request.state, "csrf_token", ""),
        "submitted": request.query_params.get("submitted") == "1",
    }
    return templates.TemplateResponse(request, "feedback_form.html", context)


@router.post("", response_model=None)
def submit_feedback(
    request: Request,
    category: str = Form(...),
    message: str = Form(...),
    contact_email: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role()),
) -> RedirectResponse | HTMLResponse:
    try:
        data = PilotFeedbackInput(
            category=category,
            message=message,
            contact_email=contact_email or None,
        )
    except ValueError as exc:
        is_admin = bool(
            current_user.role and current_user.role.name.strip().lower() == "admin"
        )
        service = PilotFeedbackService()
        context = {
            "request": request,
            "active_nav": "Pilot-Feedback & Support",
            "current_user": current_user,
            "is_admin": is_admin,
            "entries": service.list_all(db),
            "csrf_token": getattr(request.state, "csrf_token", ""),
            "error": str(exc),
        }
        return templates.TemplateResponse(
            request, "feedback_form.html", context, status_code=422
        )

    PilotFeedbackService().submit(db, data, actor=current_user.email)
    return RedirectResponse(url="/dashboard/feedback?submitted=1", status_code=303)


@router.post("/{feedback_id}/review")
def review_feedback(
    feedback_id: str,
    action: str = Form(...),
    comment: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> RedirectResponse:
    """Die Admin-Freigabe-Schleife: markiert einen Vorschlag als
    freigegeben/abgelehnt. Setzt NIEMALS selbst eine System-/Prompt-
    Änderung um - siehe app/pilot_feedback/service.py."""
    entry = get_or_404(db, PilotFeedback, feedback_id, "Feedback-Eintrag")
    try:
        PilotFeedbackService().review(
            db, entry, action=action, actor=current_user.email, comment=comment or None
        )
    except ValueError:
        pass  # unbekannte Aktion - Eintrag bleibt unveraendert sichtbar
    return RedirectResponse(url="/dashboard/feedback", status_code=303)
