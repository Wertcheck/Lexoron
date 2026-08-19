"""Ehrliche Platzhalterseiten für noch nicht gebaute Dashboard-Bereiche
(Prompt 48, erweitert um die juristische Menüstruktur aus Prompt 49).

Grundprinzip unverändert seit Prompt 48: eine Sidebar-Navigation soll
vollständig nutzbar wirken (kein "bald"-Badge, kein nicht anklickbares
Element), ohne Funktionen vorzutäuschen, die es nicht gibt. Jeder Eintrag
hier ist ein ECHTER, klickbarer Link auf eine ehrliche "in Vorbereitung"-
Seite mit einer konkreten, auf den jeweiligen Bereich zugeschnittenen
Beschreibung - kein 404, kein totes Element, aber auch keine vorgetäuschte
Fach-Funktion.

Prompt 49 (juristische Menüstruktur) hat bewusst KEINE der hier gelisteten
Funktionen tatsächlich implementiert (ausdrücklicher Auftragsumfang: "nur
Navigation/Platzhalter, keine neue Backend-Funktionen") - das gilt auch für
Bereiche, für die es dem Namen nach schon verwandte Bausteine im System
gibt (z. B. Fristen-Extraktion, Prompt 10), aber keine dedizierte
Dashboard-Seite. Echte, bereits gebaute Bereiche (Posteingang, Entwürfe,
Postausgang, Fehler, Systemstatus, Backup & Export, Nutzerverwaltung,
Konto-Bereich) werden NICHT hier, sondern in ihren eigenen bestehenden
Routern geführt - siehe app/web/account_router.py für den neuen
Profil-/Einstellungen-Bereich.

Bewusst EIN generischer, dict-getriebener Router statt vieler fast
identischer Funktionen (Prompt 48 hatte noch vier Handfunktionen - bei
jetzt 13 Platzhaltern wäre das reine Wiederholung ohne Mehrwert).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.permissions import require_login
from app.models import User
from app.web.template_paths import TEMPLATES_DIR

router = APIRouter(prefix="/dashboard", tags=["dashboard-placeholder"])

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# URL-Suffix (nach "/dashboard") -> (Sidebar-Label/active_nav, Beschreibungstext).
_PLACEHOLDER_PAGES: dict[str, tuple[str, str]] = {
    "/recent": (
        "Letzte Akten",
        "Eine Schnellübersicht der zuletzt bearbeiteten Akten befindet sich in der "
        "finalen Vorbereitung für das v0.2-Update.",
    ),
    "/matters": (
        "Aktive Akten",
        "Eine eigenständige, nach Aktenzeichen/Mandant sortierbare Akten-Übersicht "
        "(unabhängig vom Posteingang) befindet sich in der finalen Vorbereitung für "
        "das v0.2-Update.",
    ),
    "/documents": (
        "Dokumenten-Viewer",
        "Eine dedizierte Dokumentenansicht mit Vorschau befindet sich in der finalen "
        "Vorbereitung für das v0.2-Update.",
    ),
    "/archive": (
        "Archiv",
        "Eine Übersicht abgeschlossener/archivierter Akten befindet sich in der "
        "finalen Vorbereitung für das v0.2-Update.",
    ),
    "/tools/schriftsatz": (
        "Schriftsatz-Generator",
        "Ein Generator für formatierte Schriftsätze (.docx) auf Basis freigegebener "
        "Entwürfe befindet sich in der finalen Vorbereitung für das v0.2-Update.",
    ),
    "/tools/fristen": (
        "Fristen-Check",
        "Eine dedizierte Übersicht erkannter Fristen (aufbauend auf der bestehenden "
        "Fristenerkennung, Prompt 10) befindet sich in der finalen Vorbereitung für "
        "das v0.2-Update.",
    ),
    "/tools/zeitleiste": (
        "Zeitleiste",
        "Ein chronologischer Zeitleisten-Generator für Aktenverläufe befindet sich in "
        "der finalen Vorbereitung für das v0.2-Update.",
    ),
    "/tools/beleg-extraktion": (
        "Beleg-Extraktion",
        "Eine automatisierte Extraktion strukturierter Daten aus Belegen befindet "
        "sich in der finalen Vorbereitung für das v0.2-Update.",
    ),
    "/sources": (
        "Rechtsquellen",
        "Eine durchsuchbare Übersicht konfigurierter Rechtsquellen befindet sich in "
        "der finalen Vorbereitung für das v0.2-Update.",
    ),
    "/library/mustertexte": (
        "Kanzlei-Mustertexte",
        "Eine Verwaltung kanzleieigener Mustertexte befindet sich in der finalen "
        "Vorbereitung für das v0.2-Update.",
    ),
    "/library/prompts": (
        "Standard-Prompts",
        "Eine Verwaltung wiederverwendbarer Standard-Anweisungen für die "
        "KI-gestützte Entwurfserstellung befindet sich in der finalen Vorbereitung "
        "für das v0.2-Update.",
    ),
    "/knowledge": (
        "Kanzlei-Wissen",
        "Die Verwaltungsoberfläche für die Kanzlei-Wissensbasis befindet sich in der "
        "finalen Vorbereitung für das v0.2-Update.",
    ),
    "/history/analysen": (
        "Gespeicherte Analysen",
        "Ein durchsuchbares Verlaufsarchiv früherer KI-Analysen befindet sich in der "
        "finalen Vorbereitung für das v0.2-Update.",
    ),
    "/account/profile": (
        "Kanzlei-Profil & Briefkopf",
        "Die Verwaltung von Kanzleiname, Logo und Briefkopf-Einstellungen für "
        "Dokumentexporte befindet sich in der finalen Vorbereitung für das "
        "v0.2-Update.",
    ),
    "/account/license": (
        "System & Lizenz",
        "Eine Verbrauchs-/Lizenzübersicht befindet sich in der finalen Vorbereitung "
        "für das v0.2-Update. Die aktuelle Kostenauslastung ist schon heute unter "
        "Systemstatus (nur Admin) einsehbar.",
    ),
}


def _make_route(path_suffix: str, label: str, description: str) -> None:
    @router.get(path_suffix, response_class=HTMLResponse, name=f"placeholder{path_suffix}")
    def _placeholder_page(
        request: Request, current_user: User = Depends(require_login)
    ) -> HTMLResponse:
        context = {
            "request": request,
            "current_user": current_user,
            "active_nav": label,
            "placeholder_title": label,
            "placeholder_description": description,
        }
        return templates.TemplateResponse(request, "placeholder.html", context)


for _path_suffix, (_label, _description) in _PLACEHOLDER_PAGES.items():
    _make_route(_path_suffix, _label, _description)


@router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
def settings_redirect() -> HTMLResponse:
    """Rückwärtskompatibilität: die generische "Einstellungen"-Platzhalterseite
    aus Prompt 48 wurde in Prompt 49 durch den strukturierten Profil-/
    Einstellungen-Bereich (app/web/account_router.py) ersetzt. Ein Redirect
    statt eines 404 hält alte Links (u. a. im bisherigen Onboarding-Banner-
    Verlauf) funktionsfähig."""
    return RedirectResponse(url="/dashboard/account")
