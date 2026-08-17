"""Dashboard-Router für die Fehler-/Retry-Übersicht (Prompt 31).

Zugriff für ALLE drei Rollen (nicht nur Admin/Anwalt): eine fehlgeschlagene
OCR/Intake-Verarbeitung ist eine operative Wiederherstellungsaktion ohne
Kostenrisiko (kein Claude-Aufruf) und ohne besondere Sensibilität - die
bestehende Rechte-Matrix (Prompt 26) sah diesen Bereich nicht vor, daher
hier bewusst die großzügigste sinnvolle Einstufung: lesen UND manuell
wiederholen dürfen alle angemeldeten Nutzer.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_or_404
from app.auth.permissions import require_login, require_role
from app.db.session import get_db
from app.errors import ProcessingError, RetryService
from app.models import User
from app.web.template_paths import TEMPLATES_DIR

router = APIRouter(prefix="/dashboard/errors", tags=["dashboard-errors"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("", response_class=HTMLResponse)
def errors_list_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
) -> HTMLResponse:
    retry_service = RetryService()
    errors = retry_service.list_all_unresolved(db)
    context = {
        "request": request,
        "active_nav": "Fehler",
        "errors": errors,
        "current_user": current_user,
        "csrf_token": getattr(request.state, "csrf_token", ""),
    }
    return templates.TemplateResponse(request, "errors_list.html", context)


@router.post("/{error_id}/retry")
def retry_now(
    error_id: str,
    db: Session = Depends(get_db),
    # require_role() OHNE Rollen-/Berechtigungsargument: erzwingt weiterhin
    # Login + CSRF-Token (siehe app/auth/permissions.py) - konsistent mit
    # JEDER anderen mutierenden Aktion im Projekt - aber keine
    # Rolleneinschränkung, da alle drei Rollen retryen dürfen (s. o.).
    current_user: User = Depends(require_role()),
) -> RedirectResponse:
    """Löst SOFORT einen erneuten Versuch aus - ignoriert bewusst das
    Backoff-Zeitfenster (der Anwalt/Mitarbeiter weiß, dass er gerade
    manuell eingreift, z. B. nachdem er das zugrunde liegende Problem
    behoben hat, etwa Tesseract neu installiert)."""
    error = get_or_404(db, ProcessingError, error_id, "Fehlereintrag")
    retry_service = RetryService()
    try:
        retry_service.execute_retry(db, error, actor=current_user.email)
    except ValueError:
        pass  # unbekannte Operation - Fehlereintrag bleibt unverändert sichtbar
    return RedirectResponse(url="/dashboard/errors", status_code=303)
