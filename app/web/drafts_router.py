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
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_or_404
from app.attorney_instructions.schema import AttorneyInstructionInput
from app.attorney_instructions.service import AttorneyInstructionService
from app.audit.service import AuditLogService
from app.db.session import get_db
from app.drafting.versioning import create_manual_edit_version
from app.feedback.schema import DraftFeedbackInput
from app.feedback.service import DraftFeedbackService
from app.models import (
    AttorneyInstruction,
    AuditEvent,
    Document,
    Draft,
    DraftKnowledgeItemLink,
    DraftSourceLink,
    Message,
    ReviewFinding,
)
from app.web.service_factory import (
    WritingProviderNotConfiguredError,
    get_attorney_instruction_service,
    get_attorney_instruction_service_for_saving_only,
    get_drafting_service,
    get_feedback_service,
    get_review_engine,
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


def _load_original_context(draft: Draft, db: Session) -> tuple[Message | None, list[Document]]:
    """Original-Nachricht + zugehörige Dokumente, auf die dieser Entwurf
    antwortet (Split-Pane "Original links / Entwurf rechts", Design-
    Referenz des Anwalts). `draft.message_id` ist nullable - noch kein
    UI-Trigger im Posteingang erzeugt Entwürfe MIT Nachrichtenbezug (siehe
    offene Punkte im Abschlussbericht Prompt 24), daher hier ein
    ehrlicher Leerzustand statt eines Fehlers, falls nicht gesetzt."""
    if draft.message_id is None:
        return None, []
    message = db.get(Message, draft.message_id)
    if message is None:
        return None, []
    documents = db.query(Document).filter(Document.message_id == message.id).all()
    return message, documents


def _load_sources_and_knowledge(draft: Draft, db: Session):  # noqa: ANN201
    source_links = (
        db.query(DraftSourceLink)
        .options(joinedload(DraftSourceLink.source))
        .filter(DraftSourceLink.draft_id == draft.id)
        .all()
    )
    knowledge_links = (
        db.query(DraftKnowledgeItemLink)
        .options(joinedload(DraftKnowledgeItemLink.knowledge_item))
        .filter(DraftKnowledgeItemLink.draft_id == draft.id)
        .all()
    )
    return (
        [link.source for link in source_links],
        [link.knowledge_item for link in knowledge_links],
    )


def _load_findings(draft: Draft, db: Session) -> list[ReviewFinding]:
    _severity_order = {"hoch": 0, "mittel": 1, "niedrig": 2}
    findings = db.query(ReviewFinding).filter(ReviewFinding.draft_id == draft.id).all()
    return sorted(findings, key=lambda f: _severity_order.get(f.severity, 99))


def _load_audit_trail(
    draft: Draft, instructions: list[AttorneyInstruction], db: Session
) -> list[AuditEvent]:
    """Kombiniert die eigenen Audit-Events dieser Draft-Version mit denen
    ALLER AttorneyInstructions, die sich auf sie beziehen - ein
    chronologisches Bild direkt in der Entwurfsansicht (Design-Referenz:
    "Audit-Log-Panel direkt in der Entwurfsansicht sichtbar")."""
    service = AuditLogService()
    events = list(service.list_events_for_entity("Draft", draft.id, db))
    for instruction in instructions:
        events.extend(service.list_events_for_entity("AttorneyInstruction", instruction.id, db))
    return sorted(events, key=lambda e: e.created_at)


@router.get("", response_class=HTMLResponse)
def drafts_list_page(
    request: Request,
    status: str | None = None,
    show_all_versions: bool = False,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Listenansicht aller Entwürfe (Prompt 24) - standardmäßig nur die
    jeweils AKTUELLSTE Version jeder Entwurfslinie (eine Zeile, auf die
    kein anderer Draft per `previous_version_id` zurückverweist), da
    ältere Versionen für die Freigabeprüfung normalerweise nicht relevant
    sind - über die Versions-Zeitleiste in der Einzelansicht weiterhin
    einsehbar."""
    query = db.query(Draft).options(joinedload(Draft.matter))
    if status is not None:
        query = query.filter(Draft.status == status)
    all_drafts = query.order_by(Draft.updated_at.desc()).all()

    if show_all_versions:
        drafts = all_drafts
    else:
        referenced_as_previous = {
            d.previous_version_id for d in all_drafts if d.previous_version_id is not None
        }
        drafts = [d for d in all_drafts if d.id not in referenced_as_previous]

    context = {
        "request": request,
        "active_nav": "Entwürfe zur Prüfung",
        "drafts": drafts,
        "active_status": status,
        "show_all_versions": show_all_versions,
    }
    return templates.TemplateResponse(request, "drafts_list.html", context)


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
    original_message, original_documents = _load_original_context(draft, db)
    sources, knowledge_items = _load_sources_and_knowledge(draft, db)
    findings = _load_findings(draft, db)
    audit_events = _load_audit_trail(draft, instructions, db)

    context = {
        "request": request,
        "active_nav": "Entwürfe zur Prüfung",
        "draft": draft,
        "version_chain": version_chain,
        "instructions": instructions,
        "is_latest_version": version_chain[-1].id == draft.id,
        "original_message": original_message,
        "original_documents": original_documents,
        "sources": sources,
        "knowledge_items": knowledge_items,
        "findings": findings,
        "audit_events": audit_events,
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


@router.post("/{draft_id}/approve")
def approve_draft(
    draft_id: str,
    actor: str = Form(...),
    db: Session = Depends(get_db),
    service: DraftFeedbackService = Depends(get_feedback_service),
) -> RedirectResponse:
    """"Freigeben & Postausgang übergeben" (Design-Referenz des Anwalts).

    WICHTIG, ehrlich benannt: die tatsächliche Übergabe an einen
    Postausgang ist erst Prompt 25 - diese Aktion markiert den Entwurf
    über `DraftFeedbackService` als freigegeben (`status="approved"`),
    löst aber KEINEN Versand und KEINE Postausgang-Zuordnung aus (die es
    als Konzept noch nicht gibt). Kein automatischer Versand ohne
    anwaltliche Freigabe UND ohne Postausgang - Grundregel unverändert
    eingehalten."""
    draft = get_or_404(db, Draft, draft_id, "Entwurf")
    service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="approved"),
        db,
        actor=actor.strip(),
    )
    return RedirectResponse(url=f"/dashboard/drafts/{draft_id}", status_code=303)


@router.post("/{draft_id}/reject")
def reject_draft(
    draft_id: str,
    actor: str = Form(...),
    comment: str = Form(...),
    db: Session = Depends(get_db),
    service: DraftFeedbackService = Depends(get_feedback_service),
) -> RedirectResponse:
    """"Zurückweisen" - erfordert eine Begründung (siehe
    DraftFeedbackInput.rejection_requires_comment)."""
    draft = get_or_404(db, Draft, draft_id, "Entwurf")
    service.record_feedback(
        draft,
        DraftFeedbackInput(approval_status="rejected", comment=comment),
        db,
        actor=actor.strip(),
    )
    return RedirectResponse(url=f"/dashboard/drafts/{draft_id}", status_code=303)


@router.post("/{draft_id}/regenerate")
def regenerate_draft(
    draft_id: str,
    actor: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """"Neu generieren" (Design-Referenz) - Neugenerierung OHNE
    spezifische anwaltliche Anmerkung, im Unterschied zu "Änderungen
    übernehmen & neu formulieren" im Anmerkungs-Panel (das IMMER eine
    Anmerkung voraussetzt, siehe AttorneyInstructionInput). Nutzt
    `DraftingService.create_draft` direkt statt über
    `AttorneyInstructionService`, da keine Anmerkung entsteht, die
    gespeichert/verknüpft werden müsste."""
    draft = get_or_404(db, Draft, draft_id, "Entwurf")

    try:
        drafting_service = get_drafting_service()
    except WritingProviderNotConfiguredError as exc:
        return RedirectResponse(
            url=f"/dashboard/drafts/{draft_id}?error={exc}", status_code=303
        )

    result = drafting_service.create_draft(
        draft.matter_id,
        _REGENERATE_PURPOSE,
        db,
        previous_draft=draft,
        actor=actor.strip(),
    )

    if not result.success:
        reasons = "; ".join(result.blocked_reasons) or "Unbekannter Fehler"
        return RedirectResponse(
            url=f"/dashboard/drafts/{draft_id}?error=Neugenerierung blockiert: {reasons}",
            status_code=303,
        )

    return RedirectResponse(url=f"/dashboard/drafts/{result.draft_id}", status_code=303)


@router.post("/{draft_id}/review")
def review_draft(
    draft_id: str, actor: str = Form(...), db: Session = Depends(get_db)
) -> RedirectResponse:
    """"Entwurf prüfen" - löst die unabhängige Review-Engine (Prompt 18)
    aus. Findings werden von `ReviewEngine.review_draft` selbst persistiert
    (siehe app/review/engine.py) - dieser Endpunkt ruft sie nur auf und
    leitet zurück, keine eigene Persistenzlogik hier."""
    draft = get_or_404(db, Draft, draft_id, "Entwurf")

    try:
        review_engine = get_review_engine()
    except WritingProviderNotConfiguredError as exc:
        return RedirectResponse(
            url=f"/dashboard/drafts/{draft_id}?error={exc}", status_code=303
        )

    outcome = review_engine.review_draft(draft.id, db, actor=actor.strip())

    if not outcome.success:
        reasons = "; ".join(outcome.blocked_reasons) or "Unbekannter Fehler"
        return RedirectResponse(
            url=f"/dashboard/drafts/{draft_id}?error=Prüfung blockiert: {reasons}",
            status_code=303,
        )

    return RedirectResponse(url=f"/dashboard/drafts/{draft_id}", status_code=303)
