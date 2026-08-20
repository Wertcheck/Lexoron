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

import asyncio
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
from app.updater.checker import UpdateCheckResult, check_for_update
from app.web.account_router import router as account_web_router
from app.web.auth_router import router as auth_web_router
from app.web.backup_router import router as backup_web_router
from app.web.drafts_router import router as drafts_web_router
from app.web.feedback_router import router as feedback_web_router
from app.web.quality_router import router as quality_web_router
from app.web.template_paths import STATIC_DIR
from app.web.errors_router import router as errors_web_router
from app.web.monitoring_router import router as monitoring_web_router
from app.web.outbox_router import router as outbox_web_router
from app.web.placeholder_router import router as placeholder_web_router
from app.web.router import router as web_router
from app.web.users_router import router as users_web_router

logger = logging.getLogger(__name__)


async def _run_silent_update_check(app: FastAPI, manifest_url: str | None) -> None:
    """Führt die Update-Prüfung in einem Hintergrund-Thread aus (Schritt 3)
    - blockiert den App-Start nicht ("stumme" Prüfung). `check_for_update`
    fängt selbst jeden Fehler ab, daher hier kein zusätzliches try/except
    nötig."""
    result = await asyncio.to_thread(check_for_update, manifest_url)
    app.state.update_check = result
    if result.update_available:
        logger.info("Update verfügbar: %s", result.latest_version)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Laedt die validierte Konfiguration beim Start und konfiguriert das
    zentrale Logging (Prompt 32).

    Bewusst werden hier keine Werte geloggt, die Secrets enthalten koennten
    (mail_password, anthropic_api_key, session_secret_key). Nur
    unkritische Metadaten wie app_env werden zu Diagnosezwecken in
    app.state abgelegt UND geloggt.

    Seit Schritt 3 zusätzlich: eine stumme, nicht-blockierende
    Update-Prüfung im Hintergrund (siehe app/updater/checker.py) - läuft
    nebenläufig zum eigentlichen Start, verzögert ihn also nicht, und
    scheitert niemals hart (Standardwert `checked=False`, solange die
    Prüfung noch läuft oder deaktiviert ist).
    """
    settings = get_settings()
    configure_logging(log_level=settings.log_level, log_file_path=settings.log_file_path)
    app.state.settings = settings
    app.state.app_env = settings.app_env
    app.state.update_check = UpdateCheckResult(checked=False, update_available=False)
    logger.info("Anwendung gestartet (app_env=%s)", settings.app_env)
    update_task = asyncio.create_task(
        _run_silent_update_check(app, settings.update_manifest_url)
    )
    yield
    update_task.cancel()
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
app.include_router(quality_web_router)
app.include_router(account_web_router)
app.include_router(feedback_web_router)
app.include_router(placeholder_web_router)
app.mount(
    "/dashboard/static",
    StaticFiles(directory=STATIC_DIR),
    name="dashboard-static",
)
