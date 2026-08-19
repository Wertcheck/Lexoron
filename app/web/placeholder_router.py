"""Ehrliche Platzhalterseiten für noch nicht gebaute Dashboard-Bereiche
(Prompt 48, Design-/Navigations-Überarbeitung).

Vorher waren "Akten", "Rechtsquellen", "Kanzlei-Wissen" und "Einstellungen"
in der Sidebar (siehe base.html, vor Prompt 48) mit `href=None` verdrahtet
und zeigten statt eines Links ein "bald"-Badge - laut dortigem Kommentar
bewusst so, um "tote Links, die 404 werfen wuerden" zu vermeiden. Diese
Route macht daraus eine dritte, bessere Option: ein ECHTER, klickbarer Link
auf eine ehrliche "in Vorbereitung"-Seite statt entweder eines toten Links
oder eines nicht klickbaren Badges - die Navigation wirkt vollstaendig
nutzbar (passend zur Design-Vorlage), ohne etwas vorzutaeuschen, das nicht
existiert.

Bewusst EIN gemeinsames Template (`placeholder.html`) statt vier Kopien -
die einzige Variation ist Titel/Beschreibungstext.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth.permissions import require_login
from app.models import User
from app.web.template_paths import TEMPLATES_DIR

router = APIRouter(prefix="/dashboard", tags=["dashboard-placeholder"])

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# (URL-Suffix, Sidebar-Label/active_nav, Beschreibungstext)
_PLACEHOLDER_PAGES: dict[str, tuple[str, str]] = {
    "matters": (
        "Akten",
        "Eine eigenständige Akten-Übersicht (unabhängig vom Posteingang) "
        "befindet sich in der finalen Vorbereitung für das v0.2-Update.",
    ),
    "sources": (
        "Rechtsquellen",
        "Eine durchsuchbare Übersicht konfigurierter Rechtsquellen "
        "befindet sich in der finalen Vorbereitung für das v0.2-Update.",
    ),
    "knowledge": (
        "Kanzlei-Wissen",
        "Die Verwaltungsoberfläche für die Kanzlei-Wissensbasis befindet "
        "sich in der finalen Vorbereitung für das v0.2-Update.",
    ),
    "settings": (
        "Einstellungen",
        "Eine Oberfläche für Kanzlei-/Konfigurationseinstellungen befindet "
        "sich in der finalen Vorbereitung für das v0.2-Update. Bis dahin "
        "werden Einstellungen über die .env-Datei verwaltet (siehe "
        "ARCHITECTURE.md).",
    ),
}


def _render_placeholder(
    request: Request, current_user: User, label: str, description: str
) -> HTMLResponse:
    context = {
        "request": request,
        "current_user": current_user,
        "active_nav": label,
        "placeholder_title": label,
        "placeholder_description": description,
    }
    return templates.TemplateResponse(request, "placeholder.html", context)


@router.get("/matters", response_class=HTMLResponse)
def matters_placeholder(
    request: Request, current_user: User = Depends(require_login)
) -> HTMLResponse:
    label, description = _PLACEHOLDER_PAGES["matters"]
    return _render_placeholder(request, current_user, label, description)


@router.get("/sources", response_class=HTMLResponse)
def sources_placeholder(
    request: Request, current_user: User = Depends(require_login)
) -> HTMLResponse:
    label, description = _PLACEHOLDER_PAGES["sources"]
    return _render_placeholder(request, current_user, label, description)


@router.get("/knowledge", response_class=HTMLResponse)
def knowledge_placeholder(
    request: Request, current_user: User = Depends(require_login)
) -> HTMLResponse:
    label, description = _PLACEHOLDER_PAGES["knowledge"]
    return _render_placeholder(request, current_user, label, description)


@router.get("/settings", response_class=HTMLResponse)
def settings_placeholder(
    request: Request, current_user: User = Depends(require_login)
) -> HTMLResponse:
    label, description = _PLACEHOLDER_PAGES["settings"]
    return _render_placeholder(request, current_user, label, description)
