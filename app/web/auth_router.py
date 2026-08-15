"""Login/Logout/Passwortänderung (Prompt 26).

Bewusst EIGENER Router, nicht in drafts_router.py/outbox_router.py
eingemischt - Authentifizierung ist eine eigene Zuständigkeit.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user_optional, require_login
from app.auth.service import AuthService, UserService
from app.auth.session import SESSION_COOKIE_NAME, create_session_token
from app.config import Settings, get_settings
from app.db.session import get_db
from app.models import User

router = APIRouter(prefix="/dashboard", tags=["dashboard-auth"])
templates = Jinja2Templates(directory="app/web/templates")


def _set_session_cookie(response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.session_max_age_seconds,
        httponly=True,  # per JavaScript nicht auslesbar (mindert XSS-Risiko)
        secure=settings.resolved_session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    next: str = "/dashboard/inbox",  # noqa: A002
    error: str | None = None,
    current_user: User | None = Depends(get_current_user_optional),
) -> HTMLResponse:
    if current_user is not None:
        return RedirectResponse(url=next, status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"request": request, "next": next, "error": error}
    )


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/dashboard/inbox"),  # noqa: A002
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    user = AuthService().authenticate(email, password, db)
    if user is None:
        # Bewusst dieselbe, generische Fehlermeldung fuer "unbekannte
        # E-Mail" und "falsches Passwort" (siehe AuthService.authenticate).
        return RedirectResponse(
            url=f"/dashboard/login?error=E-Mail oder Passwort falsch&next={next}",
            status_code=303,
        )

    token, _csrf = create_session_token(user.id, settings)
    target = "/dashboard/change-password" if user.must_change_password else next
    response = RedirectResponse(url=target, status_code=303)
    _set_session_cookie(response, token, settings)
    return response


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    """Logout ist bewusst KEIN GET (zustandsverändernd) - CSRF-Schutz via
    Form-Feld wäre hier möglich, aber ein Logout-CSRF hat kein
    ausnutzbares Schadenspotenzial (der Angreifer könnte höchstens den
    NUTZER selbst ausloggen) - deshalb hier ohne csrf_token-Pflicht, um
    das Formular denkbar einfach zu halten."""
    response = RedirectResponse(url="/dashboard/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(
    request: Request,
    error: str | None = None,
    current_user: User = Depends(require_login),
) -> HTMLResponse:
    context = {
        "request": request,
        "error": error,
        "csrf_token": getattr(request.state, "csrf_token", ""),
        "forced": current_user.must_change_password,
        "current_user": current_user,
        "active_nav": None,
    }
    return templates.TemplateResponse(request, "change_password.html", context)


@router.post("/change-password")
def change_password_submit(
    request: Request,
    csrf_token: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
) -> RedirectResponse:
    from app.auth.permissions import verify_csrf_token
    from app.auth.security import verify_password

    verify_csrf_token(request, csrf_token)

    if not verify_password(current_password, current_user.password_hash):
        return RedirectResponse(
            url="/dashboard/change-password?error=Aktuelles Passwort ist falsch",
            status_code=303,
        )
    if len(new_password) < 10:
        return RedirectResponse(
            url="/dashboard/change-password?error=Neues Passwort muss mindestens 10 Zeichen haben",
            status_code=303,
        )
    if new_password != new_password_confirm:
        return RedirectResponse(
            url="/dashboard/change-password?error=Passwörter stimmen nicht überein",
            status_code=303,
        )

    UserService().change_password(db, current_user, new_password, actor=current_user.email)
    # Direkt zur Login-Seite umleiten und die (alte) Session-Cookie
    # löschen - NICHT über /dashboard/logout umleiten, da das eine
    # POST-only-Route ist und ein 303-Redirect vom Browser als GET
    # ausgeführt würde (405).
    response = RedirectResponse(
        url="/dashboard/login?error=Passwort geändert - bitte neu anmelden", status_code=303
    )
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response
