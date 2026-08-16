"""App-Einstiegspunkt (Prompt 02 – Repository-Grundgeruest, erweitert um
Prompt 03 – Konfigurationssystem, Prompt 21 – FastAPI-Backend,
Prompt 22 – Dashboard-Inbox und Prompt 26 – Rollen & Berechtigungen).

Bindet ab Prompt 21 das lesende REST-Backend (`app/api/`) ein, das alle
acht im Konzept geforderten Dashboard-Bereiche abdeckt: Inbox, Akten,
Dokumente, Entwuerfe, Quellen (+ Kanzlei-Wissen), Aufgaben, Einstellungen,
Audit. Siehe app/api/schemas.py fuer die Allowlist-Grundsaetze.

Ab Prompt 22 zusaetzlich das serverseitig gerenderte Dashboard
(`app/web/`, Jinja2 + HTMX) unter `/dashboard`, plus dessen statische
Assets unter `/dashboard/static`.

Ab Prompt 26: ALLE `/api/...`-Routen erfordern eine gueltige Session
(`api_router`-weite Dependency, siehe app/api/__init__.py) - kein
Endpunkt ist mehr ungeschuetzt erreichbar. Zwei Exception-Handler
uebersetzen Auth-Fehler in fuer Menschen im Browser sinnvolle Antworten
(Redirect statt rohem 401/JSON) - siehe app/auth/permissions.py fuer die
zugrunde liegenden Exception-Klassen.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.auth.permissions import ForcePasswordChangeError, NotAuthenticatedError
from app.config import get_settings
from app.observability import configure_logging
from app.web.auth_router import router as auth_web_router
from app.web.backup_router import router as backup_web_router
from app.web.drafts_router import router as drafts_web_router
from app.web.errors_router import router as errors_web_router
from app.web.monitoring_router import router as monitoring_web_router
from app.web.outbox_router import router as outbox_web_router
from app.web.router import router as web_router
from app.web.users_router import router as users_web_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Laedt die validierte Konfiguration beim Start und konfiguriert das
    zentrale Logging (Prompt 32).

    Bewusst werden hier keine Werte geloggt, die Secrets enthalten koennten
    (mail_password, anthropic_api_key, session_secret_key). Nur
    unkritische Metadaten wie app_env werden zu Diagnosezwecken in
    app.state abgelegt UND geloggt.
    """
    settings = get_settings()
    configure_logging(log_level=settings.log_level, log_file_path=settings.log_file_path)
    app.state.settings = settings
    app.state.app_env = settings.app_env
    logger.info("Anwendung gestartet (app_env=%s)", settings.app_env)
    yield
    logger.info("Anwendung wird beendet")


app = FastAPI(
    title="Kanzlei-AI-Pipeline",
    description=(
        "Konfigurierbare KI-gestuetzte Workflow-Plattform fuer eine "
        "Anwaltskanzlei (frueher Entwicklungsstand)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(NotAuthenticatedError)
def handle_not_authenticated(request: Request, exc: NotAuthenticatedError) -> RedirectResponse:
    return RedirectResponse(url=f"/dashboard/login?next={exc.next_path}", status_code=303)


@app.exception_handler(ForcePasswordChangeError)
def handle_force_password_change(
    request: Request, exc: ForcePasswordChangeError
) -> RedirectResponse:
    return RedirectResponse(url="/dashboard/change-password", status_code=303)


@app.get("/health")
def health() -> dict[str, str]:
    """Einfacher Smoke-Test-Endpunkt: bestaetigt nur, dass die App laeuft.
    Bewusst OHNE Login-Pflicht - wird u. a. fuer reine
    Infrastruktur-Healthchecks benoetigt."""
    return {"status": "ok"}


app.include_router(api_router)
app.include_router(web_router)
app.include_router(drafts_web_router)
app.include_router(outbox_web_router)
app.include_router(auth_web_router)
app.include_router(users_web_router)
app.include_router(errors_web_router)
app.include_router(monitoring_web_router)
app.include_router(backup_web_router)
app.mount(
    "/dashboard/static",
    StaticFiles(directory="app/web/static"),
    name="dashboard-static",
)
