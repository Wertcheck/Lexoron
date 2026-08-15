"""FastAPI-Backend (Prompt 21, Zugriffsschutz ab Prompt 26).

Buendelt alle Bereichs-Router zu einem einzigen `api_router`, der in
`app/main.py` eingebunden wird. Siehe app/api/schemas.py fuer die
uebergreifenden Grundsaetze (Allowlist-Schemas, nur lesende Endpunkte).

WICHTIG (Prompt 26, Vorgabe des Anwalts, woertlich): "Alle relevanten
/api/... Endpunkte muessen ebenfalls authentifiziert und autorisiert
werden." `dependencies=[Depends(require_api_login)]` auf Router-Ebene
erzwingt eine gueltige Session fuer JEDEN Endpunkt in `api_router`,
unabhaengig vom einzelnen Router - eine neue Route in einem der
Unter-Router (inbox/matters/documents/...) ist automatisch mitgeschuetzt,
ohne dass jemand daran denken muss, die Dependency dort erneut
hinzuzufuegen. `require_api_login` liefert bei fehlender Anmeldung einen
JSON-401 (nicht den Redirect der Dashboard-Variante `require_login`) -
passend fuer einen API-Client.

Es gibt aktuell KEINE mutierenden (POST/PUT/DELETE) Endpunkte in diesem
Modul (siehe app/api/schemas.py: "bewusst nur lesende Endpunkte") -
Freigeben/Zurückweisen/Neugenerieren/Versandmarkierung/Nutzerverwaltung
existieren ausschliesslich in app/web/ (dort mit `require_role`
rollenspezifisch geschuetzt). Es gibt also keinen alternativen,
API-seitigen Weg, diese Aktionen an der Dashboard-Berechtigungsprüfung
vorbei auszulösen.
"""

from fastapi import APIRouter, Depends

from app.api.routers import audit, documents, drafts, inbox, knowledge, matters, settings, sources, tasks
from app.auth.permissions import require_api_login

api_router = APIRouter(dependencies=[Depends(require_api_login)])
api_router.include_router(inbox.router)
api_router.include_router(matters.router)
api_router.include_router(documents.router)
api_router.include_router(drafts.router)
api_router.include_router(sources.router)
api_router.include_router(knowledge.router)
api_router.include_router(tasks.router)
api_router.include_router(settings.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]
