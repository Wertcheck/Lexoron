"""App-Einstiegspunkt (Prompt 02 – Repository-Grundgeruest, erweitert um
Prompt 03 – Konfigurationssystem).

Enthaelt bewusst nur ein Minimalgeruest mit einem Health-Check-Endpunkt und
dem Laden der zentralen Konfiguration. Kein Datenmodell, keine Ingestion,
keine KI-Logik, keine Mandanten-/Aktenlogik. Diese werden in den dafuer
vorgesehenen spaeteren Prompts (04 ff., siehe TODO.md) hinzugefuegt.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings


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


