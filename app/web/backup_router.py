"""Dashboard-Router für Backup/Export (Prompt 35) – NUR Admin.

Beide Aktionen erzeugen ein ZIP mit vollständigen, unpseudonymisierten
Mandanteninhalten - konsequent an die Admin-Rolle gebunden, analog zur
Systemstatus-Ansicht (Prompt 32) und Nutzerverwaltung (Prompt 26).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_or_404
from app.auth.permissions import PermissionDeniedError, require_login, require_role
from app.backup import BackupError, BackupService
from app.config import get_settings
from app.db.session import get_db
from app.export import MatterExportService
from app.models import Matter, User

router = APIRouter(prefix="/dashboard/backup", tags=["dashboard-backup"])
templates = Jinja2Templates(directory="app/web/templates")

# Eigenes, temporäres Verzeichnis für über das Dashboard erzeugte
# Archive - getrennt von einem evtl. per CLI-Skript befüllten
# `backups/`-Ordner. Wird von FileResponse gestreamt, nicht automatisch
# geloescht - siehe Betriebsdokumentation: regelmässig manuell leeren.
_DOWNLOAD_STAGING_DIR = Path(tempfile.gettempdir()) / "kanzlei_ai_dashboard_exports"


def _require_admin(current_user: User = Depends(require_login)) -> User:
    if current_user.role is None or current_user.role.name.strip().lower() != "admin":
        raise PermissionDeniedError("Nur Administratoren können Backups/Exporte erstellen")
    return current_user


@router.get("", response_class=HTMLResponse)
def backup_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
) -> HTMLResponse:
    matters = db.query(Matter).order_by(Matter.title).all()
    context = {
        "request": request,
        "active_nav": "Backup",
        "current_user": current_user,
        "matters": matters,
        "csrf_token": getattr(request.state, "csrf_token", ""),
    }
    return templates.TemplateResponse(request, "backup.html", context)


@router.post("/full")
def create_full_backup(
    current_user: User = Depends(require_role("admin")),
) -> FileResponse:
    settings = get_settings()
    service = BackupService(
        database_url=settings.database_url,
        intake_storage_dir=settings.intake_storage_dir,
        mail_attachment_storage_dir=settings.mail_attachment_storage_dir,
    )
    try:
        archive_path = service.create_backup(_DOWNLOAD_STAGING_DIR)
    except BackupError as exc:
        # Kein passender 4xx-Fehlertyp fuer "Backup fehlgeschlagen" -
        # generischer 500 ist hier ehrlicher als ein irrefuehrender
        # Berechtigungsfehler.
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return FileResponse(
        archive_path, filename=archive_path.name, media_type="application/zip"
    )


@router.post("/matter/{matter_id}")
def export_matter(
    matter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> FileResponse:
    get_or_404(db, Matter, matter_id, "Akte")  # sauberer 404 vor dem eigentlichen Export
    service = MatterExportService()
    archive_path = service.export_matter(matter_id, db, _DOWNLOAD_STAGING_DIR)
    return FileResponse(
        archive_path, filename=archive_path.name, media_type="application/zip"
    )
