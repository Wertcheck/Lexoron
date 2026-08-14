"""App-Einstiegspunkt (Prompt 02 – Repository-Grundgeruest, erweitert um
Prompt 03 – Konfigurationssystem, Prompt 21 – FastAPI-Backend und
Prompt 22 – Dashboard-Inbox).

Bindet ab Prompt 21 das lesende REST-Backend (`app/api/`) ein, das alle
acht im Konzept geforderten Dashboard-Bereiche abdeckt: Inbox, Akten,
Dokumente, Entwuerfe, Quellen (+ Kanzlei-Wissen), Aufgaben, Einstellungen,
Audit. Siehe app/api/schemas.py fuer die uebergreifenden Grundsaetze
(Allowlist-Schemas, bewusst keine Authentifizierung/Autorisierung -
folgt erst in Prompt 26).

Ab Prompt 22 zusaetzlich das serverseitig gerenderte Dashboard
(`app/web/`, Jinja2 + HTMX) unter `/dashboard`, plus dessen statische
Assets unter `/dashboard/static`.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.config import get_settings
from app.web.router import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Laedt die validierte Konfiguration beim Start.

    Bewusst werden hier keine Werte geloggt, die Secrets enthalten koennten
    (mail_password, anthropic_api_key). Nur unkritische Metadaten wie
    app_env werden zu Diagnosezwecken in app.state abgelegt.
    """
    settings = get_settings()
    app.state.settings = settings
    app.state.app_env = settings.app_env
    yield


app = FastAPI(
    title="Kanzlei-AI-Pipeline",
    description=(
        "Konfigurierbare KI-gestuetzte Workflow-Plattform fuer eine "
        "Anwaltskanzlei (frueher Entwicklungsstand)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Einfacher Smoke-Test-Endpunkt: bestaetigt nur, dass die App laeuft."""
    return {"status": "ok"}


app.include_router(api_router)
app.include_router(web_router)
app.mount(
    "/dashboard/static",
    StaticFiles(directory="app/web/static"),
    name="dashboard-static",
)


