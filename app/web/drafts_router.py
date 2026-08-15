"""Dashboard-Router für die Entwurfsansicht (Prompt 23 – Vorgriff auf
Prompt 24 "Entwürfe zur Prüfung").

Getrennt von app/web/router.py (Inbox, Prompt 22) gehalten, um dessen
Datei nicht anzufassen (Vorgabe: "keine unnötigen Umbauten außerhalb des
erforderlichen Umfangs").

WICHTIG: bewusst KEINE HTMX-Partials hier (anders als bei der Inbox) -
die Formulare dieser Seite lösen echte, folgenreiche Aktionen aus
(Neugenerierung über die Claude API, neue Versionen), volle
Seiten-Redirects nach jeder Aktion machen den Kontrollfluss einfacher
nachvollziehbar und einfacher zu testen. Kann in Prompt 24 bei Bedarf um
HTMX-Feinschliff ergänzt werden.

Es gibt (wie im gesamten Dashboard, siehe base.html-Fußnote) noch KEINE
Authentifizierung - das Feld "Ihr Kürzel" in den Formularen ist ein
manueller Platzhalter für den Actor, bis Prompt 26 echte Anmeldung bringt.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_or_404
from app.attorney_instructions.schema import AttorneyInstructionInput
from app.attorney_instructions.service import AttorneyInstructionService
from app.db.session import get_db
from app.drafting.versioning import create_manual_edit_version
from app.models import AttorneyInstruction, Draft
from app.web.service_factory import (
    WritingProviderNotConfiguredError,
    get_attorney_instruction_service,
    get_attorney_instruction_service_for_saving_only,
)

router = APIRouter(prefix="/dashboard/drafts", tags=["dashboard-drafts"])

templates = Jinja2Templates(directory="app/web/templates")

# Fest verdrahteter Schreibauftrag fuer "Aenderungen uebernehmen & neu
# formulieren" - siehe SecurityCheckService.ALLOWED_PURPOSES. Kein
# Nutzer-Freitextfeld dafuer, um versehentlich einen nicht erlaubten
# Zweck zu erzeugen.
_REGENERATE_PURPOSE = "improve_draft"


def _load_version_chain(draft: Draft, db: Session) -> list[Draft]:
    """Lädt ALLE Versionen derselben Entwurfslinie wie `draft`, sortiert
    v1 -> vN. Läuft zunächst über `previous_version_id` rückwärts bis zur
    Wurzel, sammelt dann alle Versionen der Akte, die in dieser Kette
    liegen (auch neuere, die auf `draft` zurückverweisen)."""
    all_matter_drafts = (
        db.query(Draft).filter(Draft.matter_id == draft.matter_id).all()
    )
    by_id = {d.id: d for d in all_matter_drafts}

    # Wurzel finden (v1 dieser Linie).
    current = draft
    while current.previous_version_id is not None:
        parent = by_id.get(current.previous_version_id)
        if parent is None:
            break
        current = parent
    root = current

    # Von der Wurzel aus vorwaerts entlang previous_version_id sammeln.
    children_by_parent: dict[str, list[Draft]] = {}
    for d in all_matter_drafts:
        if d.previous_version_id is not None:
            children_by_parent.setdefault(d.previous_version_id, []).append(d)

    chain = [root]
    node = root
    while True:
        children = children_by_parent.get(node.id, [])
        if not children:
            break
        # Im Normalfall genau ein Kind (lineare Kette). Bei mehreren
        # (z. B. zwei unabhaengige Bearbeitungen desselben Standes)
        # folgen wir der hoechsten Versionsnummer.
        node = max(children, key=lambda d: d.version)
        chain.append(node)
    return chain


def _load_instructions(draft: Draft, db: Session) -> list[AttorneyInstruction]:
    return (
        db.query(AttorneyInstruction)
        .filter(AttorneyInstruction.draft_id == draft.id)
        .order_by(AttorneyInstruction.created_at.desc())
        .all()
    )


@router.get("/{draft_id}", response_class=HTMLResponse)
def draft_detail_page(
    draft_id: str,
    request: Request,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    draft = get_or_404(db, Draft, draft_id, "Entwurf")
    version_chain = _load_version_chain(draft, db)
    instructions = _load_instructions(draft, db)

    context = {
        "request": request,
        "active_nav": None,
        "draft": draft,
        "version_chain": version_chain,
        "instructions": instructions,
        "is_latest_version": version_chain[-1].id == draft.id,
        "error": error,
    }
    return templates.TemplateResponse(request, "draft_detail.html", context)


@router.post("/{draft_id}/manual-edit")
def manual_edit(
    draft_id: str,
    actor: str = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Direkte manuelle Bearbeitung - erzeugt IMMER eine neue Version,
    verändert die aktuelle Zeile nicht (siehe create_manual_edit_version)."""
    draft = get_or_404(db, Draft, draft_id, "Entwurf")

    new_draft = create_manual_edit_version(
        db,
        previous_draft=draft,
        new_content=content,
        status="draft",
        actor=actor.strip(),
        details=f"Manuelle Bearbeitung von Draft {draft.id} im Dashboard",
    )
    return RedirectResponse(
        url=f"/dashboard/drafts/{new_draft.id}", status_code=303
    )


@router.post("/{draft_id}/instructions")
def save_instruction(
    draft_id: str,
    actor: str = Form(...),
    instruction_text: str = Form(...),
    db: Session = Depends(get_db),
    service: AttorneyInstructionService = Depends(
        get_attorney_instruction_service_for_saving_only
    ),
) -> RedirectResponse:
    """"Anmerkung speichern" - legt NUR den Eintrag an, löst KEINE
    Neugenerierung aus. Braucht deshalb bewusst KEINEN vollen
    DraftingService (siehe service_factory.py) - funktioniert auch ohne
    konfigurierten Claude-API-Key."""
    draft = get_or_404(db, Draft, draft_id, "Entwurf")
    service.create_instruction(
        draft,
        AttorneyInstructionInput(instruction_text=instruction_text),
        db,
        actor=actor.strip(),
    )
    return RedirectResponse(url=f"/dashboard/drafts/{draft_id}", status_code=303)


@router.post("/{draft_id}/instructions/apply")
def save_and_apply_instruction(
    draft_id: str,
    actor: str = Form(...),
    instruction_text: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """"Änderungen übernehmen & neu formulieren" - speichert die Anmerkung
    UND löst sofort eine Neugenerierung darüber aus (voller Privacy-
    Gateway-Durchlauf, siehe AttorneyInstructionService.apply_instruction).
    """
    draft = get_or_404(db, Draft, draft_id, "Entwurf")

    try:
        service = get_attorney_instruction_service()
    except WritingProviderNotConfiguredError as exc:
        return RedirectResponse(
            url=f"/dashboard/drafts/{draft_id}?error={exc}", status_code=303
        )

    instruction = service.create_instruction(
        draft,
        AttorneyInstructionInput(instruction_text=instruction_text),
        db,
        actor=actor.strip(),
    )
    result = service.apply_instruction(
        instruction,
        db,
        purpose=_REGENERATE_PURPOSE,
        actor=actor.strip(),
    )

    if not result.drafting_result.success:
        reasons = "; ".join(result.drafting_result.blocked_reasons) or "Unbekannter Fehler"
        return RedirectResponse(
            url=f"/dashboard/drafts/{draft_id}?error=Neugenerierung blockiert: {reasons}",
            status_code=303,
        )

    return RedirectResponse(
        url=f"/dashboard/drafts/{result.new_draft.id}", status_code=303
    )
