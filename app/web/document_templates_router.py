"""Dashboard-Router für 'Kanzleiwissen & KI' -> 'Kanzlei-Mustertexte'
(Block 3, 20.08.) – löst den bisherigen Platzhalter unter
`/dashboard/library/mustertexte` ab (siehe app/web/placeholder_router.py).

Verwaltung der Dokumentvorlagen für den Dokumentengenerator (siehe
app/document_generator/ und app/web/document_generator_router.py). Rechte
analog zur bestehenden Standard-Prompts-Bibliothek
(app/web/prompt_library_router.py): Lesen für alle drei Rollen, Anlegen/
Ändern/Löschen auf Admin/Anwalt beschränkt (Mitarbeiter generiert/bearbeitet
Dokumente aus bestehenden Vorlagen, kuratiert aber keine Vorlagen selbst -
gleiches Prinzip wie bei Kanzlei-Prompts)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_or_404
from app.auth.permissions import PermissionDeniedError, require_login, require_role
from app.db.session import get_db
from app.document_generator.placeholders import SUPPORTED_PLACEHOLDERS, extract_placeholders
from app.document_generator.schema import DocumentTemplateInput
from app.document_generator.template_service import (
    DocumentTemplateHasGeneratedDocumentsError,
    DocumentTemplateService,
)
from app.models import DocumentTemplate, User
from app.web.template_paths import TEMPLATES_DIR

router = APIRouter(prefix="/dashboard/library/mustertexte", tags=["dashboard-document-templates"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _is_curator(current_user: User) -> bool:
    return bool(
        current_user.role and current_user.role.name.strip().lower() in {"admin", "anwalt"}
    )


@router.get("", response_class=HTMLResponse)
def document_templates_page(
    request: Request,
    error: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
) -> HTMLResponse:
    templates_with_placeholders = [
        (template, extract_placeholders(template.content))
        for template in DocumentTemplateService().list_templates(db)
    ]
    context = {
        "request": request,
        "active_nav": "Kanzlei-Mustertexte",
        "current_user": current_user,
        "is_curator": _is_curator(current_user),
        "templates_with_placeholders": templates_with_placeholders,
        "supported_placeholders": SUPPORTED_PLACEHOLDERS,
        "csrf_token": getattr(request.state, "csrf_token", ""),
        "error": error,
    }
    return templates.TemplateResponse(request, "document_templates.html", context)


@router.post("")
def create_document_template(
    request: Request,
    name: str = Form(...),
    category: str = Form(""),
    description: str = Form(""),
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "anwalt")),
) -> RedirectResponse:
    try:
        data = DocumentTemplateInput(
            name=name, category=category or None, description=description or None, content=content
        )
    except ValueError as exc:
        return RedirectResponse(
            url=f"/dashboard/library/mustertexte?error={exc}", status_code=303
        )
    DocumentTemplateService().create_template(db, data, actor=current_user.email)
    return RedirectResponse(url="/dashboard/library/mustertexte", status_code=303)


@router.get("/{template_id}/edit", response_class=HTMLResponse)
def edit_document_template_page(
    template_id: str,
    request: Request,
    error: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
) -> HTMLResponse:
    if not _is_curator(current_user):
        raise PermissionDeniedError("Nur Admin/Anwalt können Dokumentvorlagen bearbeiten")

    template = get_or_404(db, DocumentTemplate, template_id, "Dokumentvorlage")
    context = {
        "request": request,
        "active_nav": "Kanzlei-Mustertexte",
        "current_user": current_user,
        "template": template,
        "supported_placeholders": SUPPORTED_PLACEHOLDERS,
        "csrf_token": getattr(request.state, "csrf_token", ""),
        "error": error,
    }
    return templates.TemplateResponse(request, "document_template_edit.html", context)


@router.post("/{template_id}")
def update_document_template(
    template_id: str,
    name: str = Form(...),
    category: str = Form(""),
    description: str = Form(""),
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "anwalt")),
) -> RedirectResponse:
    template = get_or_404(db, DocumentTemplate, template_id, "Dokumentvorlage")
    try:
        data = DocumentTemplateInput(
            name=name, category=category or None, description=description or None, content=content
        )
    except ValueError as exc:
        return RedirectResponse(
            url=f"/dashboard/library/mustertexte/{template_id}/edit?error={exc}", status_code=303
        )
    DocumentTemplateService().update_template(db, template, data, actor=current_user.email)
    return RedirectResponse(url="/dashboard/library/mustertexte", status_code=303)


@router.post("/{template_id}/delete")
def delete_document_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "anwalt")),
) -> RedirectResponse:
    template = get_or_404(db, DocumentTemplate, template_id, "Dokumentvorlage")
    try:
        DocumentTemplateService().delete_template(db, template, actor=current_user.email)
    except DocumentTemplateHasGeneratedDocumentsError as exc:
        return RedirectResponse(
            url=f"/dashboard/library/mustertexte?error={exc}", status_code=303
        )
    return RedirectResponse(url="/dashboard/library/mustertexte", status_code=303)
