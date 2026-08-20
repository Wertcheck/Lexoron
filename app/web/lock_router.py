"""App-Sperre / PIN-Lock – Entsperr-Seite + Sperren-Auslöser (Schritt 3).

Bewusst EIGENER Router, nicht in auth_router.py (Login/Logout/Passwort)
eingemischt - die PIN-Sperre ist konzeptionell etwas anderes (kein
Authentifizierungswechsel, nur ein zusätzliches Gate INNERHALB einer
bereits laufenden Session, siehe app/auth/pin_lock.py)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.permissions import (
    get_current_user_optional,
    require_login,
    require_role,
    verify_csrf_token,
)
from app.auth.pin_lock import PinLockService, PinValidationError
from app.config import get_settings
from app.db.session import get_db
from app.models import User
from app.web.template_paths import TEMPLATES_DIR

router = APIRouter(prefix="/dashboard", tags=["dashboard-lock"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/lock-config")
def lock_config(request: Request, current_user: User = Depends(require_login)) -> dict:
    """Kleiner, eigenständiger JSON-Endpunkt (Schritt 3) - liefert der
    clientseitigen Inaktivitäts-Logik in base.html, ob überhaupt eine PIN
    eingerichtet ist (ohne PIN bleibt der Sperren-Button/Timer inaktiv,
    sonst gäbe es keinen Weg zurück), nach wie vielen Minuten Inaktivität
    automatisch gesperrt werden soll, UND das CSRF-Token für den
    Sperren-Button. Bewusst als separater Endpunkt statt in jeden einzelnen
    Router-Kontext injiziert (identisches Muster zu den HTMX-Badges
    budget-badge/update-badge) - insbesondere die Platzhalterseiten
    (app/web/placeholder_router.py) setzen `csrf_token` nicht in ihrem
    Kontext, ein rein Jinja-basierter Ansatz wäre dort leer geblieben."""
    settings = get_settings()
    return {
        "pin_configured": current_user.pin_hash is not None,
        "inactivity_minutes": settings.pin_lock_inactivity_minutes,
        "csrf_token": getattr(request.state, "csrf_token", ""),
    }


@router.get("/unlock", response_class=HTMLResponse)
def unlock_page(
    request: Request,
    error: str | None = None,
    current_user: User | None = Depends(get_current_user_optional),
) -> HTMLResponse:
    if current_user is None:
        return RedirectResponse(url="/dashboard/login", status_code=303)
    if not current_user.is_locked:
        return RedirectResponse(url="/dashboard/inbox", status_code=303)
    context = {
        "request": request,
        "error": error,
        "csrf_token": getattr(request.state, "csrf_token", ""),
        "current_user": current_user,
        "active_nav": None,
    }
    return templates.TemplateResponse(request, "unlock.html", context)


@router.post("/unlock")
def unlock_submit(
    request: Request,
    csrf_token: str = Form(...),
    pin: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> RedirectResponse:
    if current_user is None:
        return RedirectResponse(url="/dashboard/login", status_code=303)
    verify_csrf_token(request, csrf_token)

    if not PinLockService().unlock(db, current_user, pin):
        return RedirectResponse(url="/dashboard/unlock?error=Falsche PIN", status_code=303)
    return RedirectResponse(url="/dashboard/inbox", status_code=303)


@router.post("/lock-now")
def lock_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role()),
) -> RedirectResponse:
    """Manuelles Sperren - ausgelöst über den Sperren-Button in der Kopfzeile
    (base.html) ODER den clientseitigen Inaktivitäts-Timer. Kein-Op-Fehler
    (statt einer 500er-Seite), falls der Nutzer keine PIN eingerichtet hat -
    der Button erscheint clientseitig ohnehin nur mit eingerichteter PIN,
    aber ein direkter POST-Aufruf ohne PIN soll trotzdem nicht abstürzen."""
    try:
        PinLockService().lock(db, current_user)
    except PinValidationError:
        pass
    return RedirectResponse(url="/dashboard/unlock", status_code=303)
