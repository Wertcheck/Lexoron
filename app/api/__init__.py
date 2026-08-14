"""FastAPI-Backend (Prompt 21).

Buendelt alle Bereichs-Router zu einem einzigen `api_router`, der in
`app/main.py` eingebunden wird. Siehe app/api/schemas.py fuer die
uebergreifenden Grundsaetze (Allowlist-Schemas, keine Authentifizierung,
nur lesende Endpunkte).
"""

from fastapi import APIRouter

from app.api.routers import audit, documents, drafts, inbox, knowledge, matters, settings, sources, tasks

api_router = APIRouter()
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
