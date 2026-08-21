"""Universal Command Bar (Strg+K/⌘K, 20.08.) – globale Hybrid-Suche über
Mandanten, Akten, Dokumente (lokal) und Rechtsquellen (siehe
app/search/global_search_service.py für die Trennlogik "Lokal"/"Extern").

Liefert eine HTML-Partial (kein JSON) - dasselbe HTMX-Muster wie
partials/api_reachability_result.html: der `<input>` im
Command-Bar-Modal (app/web/templates/base.html) triggert per
`hx-trigger="input changed delay:300ms"` (Live-Suche mit Debounce, siehe
Aufgabenstellung) direkt gegen diese Route, kein separates JSON-/JS-
Rendering noetig."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.permissions import require_login
from app.db.session import get_db
from app.models import User
from app.search.global_search_service import MIN_QUERY_LENGTH
from app.web.service_factory import get_global_search_service
from app.web.template_paths import TEMPLATES_DIR

router = APIRouter(prefix="/dashboard/search", tags=["dashboard-global-search"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)

_RESULTS_LIMIT_PER_CATEGORY = 5


@router.get("/results", response_class=HTMLResponse)
def global_search_results(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
) -> HTMLResponse:
    service = get_global_search_service()
    results = service.search(q, db, limit_per_category=_RESULTS_LIMIT_PER_CATEGORY)
    context = {
        "request": request,
        "query": q.strip(),
        "results": results,
        "min_length": MIN_QUERY_LENGTH,
    }
    return templates.TemplateResponse(request, "partials/global_search_results.html", context)
