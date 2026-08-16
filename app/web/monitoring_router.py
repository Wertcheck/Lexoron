"""Systemstatus-Ansicht (Prompt 32) – NUR für Admin.

Zeigt operative Kennzahlen (Anzahl offener/dauerhaft fehlgeschlagener
Fehler-/Retry-Einträge, Konfigurationsstatus als reine Ja/Nein-Werte,
Umgebung) - NIEMALS Mandanteninhalte oder Secrets. Bewusst NICHT auf
`/health` (das bleibt absichtlich unauthentifiziert und minimal, siehe
app/main.py, für reine Infrastruktur-Healthchecks) - diese Ansicht zeigt
mehr Detail und ist daher an eine Anmeldung UND die Admin-Rolle gebunden,
um auch geringfügige operative Informationspreisgabe zu vermeiden.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.permissions import PermissionDeniedError, require_login
from app.config import get_settings
from app.cost_control import CostControlService
from app.db.session import get_db
from app.models import AuditEvent, ProcessingError, User

router = APIRouter(prefix="/dashboard/monitoring", tags=["dashboard-monitoring"])
templates = Jinja2Templates(directory="app/web/templates")


def _require_admin(current_user: User = Depends(require_login)) -> User:
    if current_user.role is None or current_user.role.name.strip().lower() != "admin":
        raise PermissionDeniedError("Nur Administratoren können den Systemstatus einsehen")
    return current_user


@router.get("", response_class=HTMLResponse)
def monitoring_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
) -> HTMLResponse:
    settings = get_settings()

    pending_count = (
        db.query(func.count(ProcessingError.id))
        .filter(ProcessingError.status == "pending_retry")
        .scalar()
    )
    failed_permanent_count = (
        db.query(func.count(ProcessingError.id))
        .filter(ProcessingError.status == "failed_permanent")
        .scalar()
    )
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar()

    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    recent_audit_count = (
        db.query(func.count(AuditEvent.id))
        .filter(AuditEvent.created_at >= one_day_ago)
        .scalar()
    )

    cost_control = CostControlService()
    current_month_spend = cost_control.get_current_month_spend_usd(db)
    total_spend = cost_control.get_total_spend_usd(db)
    monthly_budget = settings.monthly_budget_usd
    budget_percent_used = (
        round((current_month_spend / monthly_budget) * 100, 1)
        if monthly_budget and monthly_budget > 0
        else None
    )

    context = {
        "request": request,
        "active_nav": "Systemstatus",
        "current_user": current_user,
        "app_env": settings.app_env,
        "ocr_enabled": settings.ocr_enabled,
        "mail_configured": settings.mail_password is not None,
        "claude_api_configured": settings.anthropic_api_key is not None,
        "session_cookie_secure": settings.resolved_session_cookie_secure,
        "pending_error_count": pending_count,
        "failed_permanent_error_count": failed_permanent_count,
        "total_users": total_users,
        "active_users": active_users,
        "recent_audit_count_24h": recent_audit_count,
        "current_month_spend_usd": current_month_spend,
        "total_spend_usd": total_spend,
        "monthly_budget_usd": monthly_budget,
        "budget_percent_used": budget_percent_used,
    }
    return templates.TemplateResponse(request, "monitoring.html", context)
