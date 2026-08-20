"""Systemstatus-Ansicht (Prompt 32) – NUR für Admin.

Zeigt operative Kennzahlen (Anzahl offener/dauerhaft fehlgeschlagener
Fehler-/Retry-Einträge, Konfigurationsstatus als reine Ja/Nein-Werte,
Umgebung) - NIEMALS Mandanteninhalte oder Secrets. Bewusst NICHT auf
`/health` (das bleibt absichtlich unauthentifiziert und minimal, siehe
app/main.py, für reine Infrastruktur-Healthchecks) - diese Ansicht zeigt
mehr Detail und ist daher an eine Anmeldung UND die Admin-Rolle gebunden,
um auch geringfügige operative Informationspreisgabe zu vermeiden.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.permissions import PermissionDeniedError, require_login, require_role
from app.config import get_settings
from app.cost_control import CostControlService
from app.db.session import get_db
from app.logs import LogAccessService
from app.models import AuditEvent, ProcessingError, User
from app.ollama_setup import OllamaInstallerService, OllamaInstallProgress
from app.setup.paths import resolve_data_dir
from app.system_health import SystemHealthService
from app.web.template_paths import TEMPLATES_DIR

router = APIRouter(prefix="/dashboard/monitoring", tags=["dashboard-monitoring"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _require_admin(current_user: User = Depends(require_login)) -> User:
    if current_user.role is None or current_user.role.name.strip().lower() != "admin":
        raise PermissionDeniedError("Nur Administratoren können den Systemstatus einsehen")
    return current_user


def _disk_check_path(database_url: str):  # -> Path
    """Prüft den Speicherplatz dort, wo die Anwendung tatsächlich Daten
    ablegt: bei SQLite das Verzeichnis der Datenbankdatei (i. d. R.
    dieselbe Partition wie die Dokumentenspeicher), sonst als sinnvoller
    Fallback das per Prompt 36/37 aufgelöste Datenverzeichnis
    (%PROGRAMDATA%\\KanzleiAI)."""
    from pathlib import Path

    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.removeprefix("sqlite:///")).resolve()
        return db_path.parent if str(db_path.parent) not in ("", ".") else Path.cwd()
    return resolve_data_dir()


@router.get("/budget-badge", response_class=HTMLResponse)
def budget_badge(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
) -> HTMLResponse:
    """Unaufdringlicher Hinweis zum lokalen EUR-Softlimit (Schritt 3) - für
    ALLE angemeldeten Nutzer sichtbar (nicht nur Admin), da ein erreichtes
    Softlimit die tägliche Arbeit aller betrifft. Zeigt bewusst NUR den
    Prozentsatz, keine absoluten Beträge/Einzelaufrufe - Details bleiben
    der admin-only Systemstatus-Seite vorbehalten. Bleibt leer (kein
    Markup), solange das Limit nicht erreicht ist - kein Dauer-Badge."""
    status = CostControlService().get_soft_limit_status(db)
    context = {"request": request, "status": status}
    return templates.TemplateResponse(request, "partials/budget_badge.html", context)


@router.get("/update-badge", response_class=HTMLResponse)
def update_badge(request: Request, current_user: User = Depends(require_login)) -> HTMLResponse:
    """Unaufdringlicher Hinweis auf eine verfügbare Programmversion
    (Schritt 3) - liest ausschließlich das beim Start bereits ermittelte
    Ergebnis aus `app.state.update_check` (kein erneuter Netzwerkaufruf pro
    Seitenaufruf). Bewusst kein Auto-Download/-Installation - nur ein Link
    zur manuellen Installation durch den Admin."""
    update_check = getattr(request.app.state, "update_check", None)
    context = {"request": request, "update_check": update_check}
    return templates.TemplateResponse(request, "partials/update_badge.html", context)


@router.get("/ollama-badge", response_class=HTMLResponse)
def ollama_badge(request: Request, current_user: User = Depends(require_login)) -> HTMLResponse:
    """Sichtbarer KI-Modus-/Ollama-Status fuer JEDE angemeldete Person auf
    JEDER Seite (Auftrag 20.08.: "Live-Status-Badge... prominent") - wie
    `update_badge` oben liest dies ausschließlich das beim Start bereits
    ermittelte `app.state.ollama_check` (siehe app/main.py:
    _run_silent_ollama_check), KEIN erneuter Netzwerkaufruf pro
    Seitenaufruf/pro Nutzer (derselbe Grundsatz wie bei allen anderen
    Erreichbarkeitschecks in diesem Projekt). Eine erneute, aktive Prüfung
    bleibt admin-only und explizit (siehe /check-ollama, Systemstatus-/
    Einstellungsseite)."""
    settings = get_settings()
    ollama_check = getattr(request.app.state, "ollama_check", None)
    context = {
        "request": request,
        "ai_mode": settings.ai_mode,
        "ollama_model_name": settings.ollama_model_name,
        "ollama_check": ollama_check,
    }
    return templates.TemplateResponse(request, "partials/ollama_badge.html", context)


@router.post("/check-api", response_class=HTMLResponse)
def check_api_reachability(
    request: Request,
    current_user: User = Depends(require_role("admin")),
) -> HTMLResponse:
    """Löst GENAU EINEN, ausschließlich per Admin-Klick ausgelösten
    Erreichbarkeitscheck aus (siehe SystemHealthService-Docstring für die
    Begründung, warum das nicht automatisch bei jedem Seitenaufruf
    passiert)."""
    settings = get_settings()
    api_key = (
        settings.anthropic_api_key.get_secret_value()
        if settings.anthropic_api_key is not None
        else None
    )
    result = SystemHealthService().check_claude_api_reachability(api_key)
    context = {"request": request, "result": result}
    return templates.TemplateResponse(request, "partials/api_reachability_result.html", context)


@router.post("/check-ollama", response_class=HTMLResponse)
def check_ollama_reachability(
    request: Request,
    current_user: User = Depends(require_role("admin")),
) -> HTMLResponse:
    """Wie `check_api_reachability`, für den lokalen Ollama-Dienst
    (Local-First-Architektur, siehe ARCHITECTURE.md §60)."""
    settings = get_settings()
    result = SystemHealthService().check_ollama_reachability(settings.ollama_base_url)
    context = {"request": request, "result": result}
    return templates.TemplateResponse(request, "partials/api_reachability_result.html", context)


# --- Geführter Ollama-Installations-/Update-Assistent (20.08.) ---
#
# Verhindert einen doppelten, gleichzeitig laufenden Installationsversuch
# (z. B. zweiter Klick waehrend eines laufenden Downloads) - EIN
# Prozess-weiter Lock reicht (Single-Instance-App, siehe run.py:
# _acquire_single_instance_lock fuer dasselbe Grundprinzip auf
# Anwendungsebene). Der eigentliche Fortschritt lebt in `app.state`
# (dieselbe Ablage wie `app.state.ollama_check`/`app.state.update_check`),
# NICHT in der Datenbank - rein transienter Laufzeit-Status.
_ollama_install_lock = threading.Lock()


def _run_ollama_install_in_background(app_state: object) -> None:
    def _on_progress(progress: OllamaInstallProgress) -> None:
        app_state.ollama_install_progress = progress  # type: ignore[attr-defined]

    try:
        OllamaInstallerService().run_guided_install(_on_progress)
    finally:
        _ollama_install_lock.release()


@router.post("/ollama-install/start", response_class=HTMLResponse)
def start_ollama_install(
    request: Request,
    current_user: User = Depends(require_role("admin")),
) -> HTMLResponse:
    """Startet den geführten Download+Installation/Update NUR auf diesen
    expliziten Admin-Klick hin (siehe app/ollama_setup/service.py-
    Moduldocstring zur "keine automatische externe Kommunikation ohne
    explizite Freigabe"-Leitplanke) - läuft in einem eigenen Hintergrund-
    Thread, damit dieser Request selbst sofort zurückkehrt (Download +
    UAC-Elevation + Erreichbarkeits-Polling können mehrere Minuten dauern).
    Ein bereits laufender Versuch wird NICHT doppelt gestartet - der Klick
    liefert dann einfach den aktuellen Fortschritt zurück."""
    if _ollama_install_lock.acquire(blocking=False):
        request.app.state.ollama_install_progress = OllamaInstallProgress(
            status="downloading", message="Ollama-Setup wird heruntergeladen…"
        )
        threading.Thread(
            target=_run_ollama_install_in_background,
            args=(request.app.state,),
            daemon=True,
        ).start()

    progress = getattr(
        request.app.state, "ollama_install_progress", OllamaInstallProgress()
    )
    context = {"request": request, "progress": progress}
    return templates.TemplateResponse(request, "partials/ollama_install_progress.html", context)


@router.get("/ollama-install/status", response_class=HTMLResponse)
def ollama_install_status(
    request: Request, current_user: User = Depends(_require_admin)
) -> HTMLResponse:
    """Wird vom Frontend per `setInterval` gepollt, während ein Vorgang
    läuft (siehe partials/ollama_install_widget.html) - liefert denselben
    Fortschritts-Partial wie `/ollama-install/start`."""
    progress = getattr(
        request.app.state, "ollama_install_progress", OllamaInstallProgress()
    )
    context = {"request": request, "progress": progress}
    return templates.TemplateResponse(request, "partials/ollama_install_progress.html", context)


@router.get("/logs-preview", response_class=HTMLResponse)
def logs_preview(request: Request, current_user: User = Depends(_require_admin)) -> HTMLResponse:
    settings = get_settings()
    lines = LogAccessService().read_tail(settings.log_file_path, max_lines=50)
    context = {
        "request": request,
        "lines": lines,
        "log_file_configured": settings.log_file_path is not None,
    }
    return templates.TemplateResponse(request, "partials/logs_preview.html", context)


@router.get("/logs/download")
def download_logs(current_user: User = Depends(_require_admin)) -> PlainTextResponse:
    settings = get_settings()
    content = LogAccessService().anonymized_download_content(settings.log_file_path)
    if content is None:
        content = "Keine Log-Datei konfiguriert oder Datei noch nicht vorhanden.\n"
    return PlainTextResponse(
        content,
        headers={
            "Content-Disposition": 'attachment; filename="kanzlei_ai_log_anonymisiert.txt"'
        },
    )


@router.get("", response_class=HTMLResponse)
def monitoring_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
) -> HTMLResponse:
    settings = get_settings()
    health_service = SystemHealthService()
    disk_status = health_service.check_disk_space(_disk_check_path(settings.database_url))
    database_status = health_service.check_database_status(db, settings.database_url)

    pending_count = (
        db.query(func.count(ProcessingError.id))
        .filter(ProcessingError.status == "pending_retry")
        .scalar()
    )
    failed_permanent_count = (
        db.query(func.count(ProcessingError.id))
        .filter(ProcessingError.status == "failed_permanent")
        .scalar()
    )
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar()

    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    recent_audit_count = (
        db.query(func.count(AuditEvent.id))
        .filter(AuditEvent.created_at >= one_day_ago)
        .scalar()
    )

    cost_control = CostControlService()
    current_month_spend = cost_control.get_current_month_spend_usd(db)
    total_spend = cost_control.get_total_spend_usd(db)
    monthly_budget = settings.monthly_budget_usd
    budget_percent_used = (
        round((current_month_spend / monthly_budget) * 100, 1)
        if monthly_budget and monthly_budget > 0
        else None
    )

    context = {
        "request": request,
        "active_nav": "Systemstatus",
        "current_user": current_user,
        "app_env": settings.app_env,
        "ocr_enabled": settings.ocr_enabled,
        "mail_configured": settings.mail_password is not None,
        "claude_api_configured": settings.anthropic_api_key is not None,
        "ai_mode": settings.ai_mode,
        "session_cookie_secure": settings.resolved_session_cookie_secure,
        "pending_error_count": pending_count,
        "failed_permanent_error_count": failed_permanent_count,
        "total_users": total_users,
        "active_users": active_users,
        "recent_audit_count_24h": recent_audit_count,
        "current_month_spend_usd": current_month_spend,
        "total_spend_usd": total_spend,
        "monthly_budget_usd": monthly_budget,
        "budget_percent_used": budget_percent_used,
        "disk_status": disk_status,
        "database_status": database_status,
        "log_file_configured": settings.log_file_path is not None,
        "csrf_token": getattr(request.state, "csrf_token", ""),
    }
    return templates.TemplateResponse(request, "monitoring.html", context)
