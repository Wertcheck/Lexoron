"""Rechte-Matrix + FastAPI-Dependencies für Login-Pflicht, Rollenprüfung
und CSRF-Schutz (Prompt 26).

WICHTIG (Vorgabe des Anwalts, wörtlich): "Die Berechtigungen dürfen nicht
nur durch das UI erzwungen werden. Jede geschützte Aktion muss zusätzlich
serverseitig/API-seitig geprüft werden." Jede Dependency hier prüft
IMMER serverseitig - ein ausgeblendeter Button im Template ist reine
UX-Höflichkeit, NIEMALS die eigentliche Durchsetzung. `require_role`
wird direkt in den Router-Funktionssignaturen verwendet (nicht nur im
Template), sodass ein direkter POST-Aufruf (curl, Skript, manipuliertes
Formular) exakt denselben Prüfungen unterliegt wie ein Klick im Dashboard.

RECHTE-MATRIX (wörtliche Vorgabe des Anwalts):

- ADMIN: alles, inkl. Nutzer-/Rollenverwaltung.
- ANWALT: vollständiger fachlicher Workflow (lesen, Anmerkungen, manuelle
  Bearbeitung, Claude-Neugenerierung, freigeben, zurückweisen, als
  versendet markieren) - KEINE Nutzer-/Rollenverwaltung.
- MITARBEITER: lesen, manuelle Bearbeitung, Anmerkungen erstellen/
  speichern - KEINE Claude-Neugenerierung, KEINE Freigabe/Zurückweisung/
  Versandmarkierung, KEINE Nutzerverwaltung.

Die drei Rollen selbst sind Datenbank-Seed-Daten (siehe app/models/role.py),
die Zuordnung Rolle -> Berechtigungen ist bewusst eine feste, im Code
nachvollziehbare Tabelle (PERMISSION_MATRIX unten) - siehe
app/models/role.py-Docstring und ARCHITECTURE.md §38 für die Abwägung.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.session import SESSION_COOKIE_NAME, read_session_token
from app.config import Settings, get_settings
from app.db.session import get_db
from app.models import User

# --- Berechtigungs-Konstanten ---
# Ein Claude-API-Aufruf (Neugenerierung UND Review-Engine-Prüfung - beide
# kostenpflichtig und lösen einen externen API-Call aus) wird EINHEITLICH
# unter PERM_CLAUDE_CALL gefasst - die Vorgabe nennt "Claude-Neugenerierung
# auslösen" nicht separat "Entwurf prüfen", beide sind aber vom selben
# Kostenrisiko betroffen, siehe Analyse vor Freigabe dieses Prompts.
PERM_DASHBOARD_READ = "dashboard:read"
PERM_DRAFT_MANUAL_EDIT = "draft:manual_edit"
PERM_INSTRUCTION_CREATE = "instruction:create"
PERM_CLAUDE_CALL = "claude:call"
PERM_DRAFT_APPROVE = "draft:approve"
PERM_DRAFT_REJECT = "draft:reject"
PERM_OUTBOX_MARK_SENT = "outbox:mark_sent"
PERM_USER_MANAGE = "user:manage"

_ALL_PERMISSIONS = frozenset(
    {
        PERM_DASHBOARD_READ,
        PERM_DRAFT_MANUAL_EDIT,
        PERM_INSTRUCTION_CREATE,
        PERM_CLAUDE_CALL,
        PERM_DRAFT_APPROVE,
        PERM_DRAFT_REJECT,
        PERM_OUTBOX_MARK_SENT,
        PERM_USER_MANAGE,
    }
)

PERMISSION_MATRIX: dict[str, frozenset[str]] = {
    "admin": _ALL_PERMISSIONS,
    "anwalt": frozenset(
        {
            PERM_DASHBOARD_READ,
            PERM_DRAFT_MANUAL_EDIT,
            PERM_INSTRUCTION_CREATE,
            PERM_CLAUDE_CALL,
            PERM_DRAFT_APPROVE,
            PERM_DRAFT_REJECT,
            PERM_OUTBOX_MARK_SENT,
        }
    ),
    "mitarbeiter": frozenset(
        {
            PERM_DASHBOARD_READ,
            PERM_DRAFT_MANUAL_EDIT,
            PERM_INSTRUCTION_CREATE,
        }
    ),
}


def has_permission(user: User, permission: str) -> bool:
    if not user.is_active or user.role is None:
        return False
    role_name = user.role.name.strip().lower()
    return permission in PERMISSION_MATRIX.get(role_name, frozenset())


class NotAuthenticatedError(Exception):
    """Wird von `require_login`/`require_role` ausgelöst, wenn keine
    gültige Session vorliegt. Für Web-Routen von einem Exception-Handler
    (siehe app/main.py) zu einem Redirect auf /dashboard/login übersetzt."""

    def __init__(self, next_path: str = "/dashboard/inbox") -> None:
        self.next_path = next_path


class ForcePasswordChangeError(Exception):
    """Wird ausgelöst, wenn ein Nutzer mit `must_change_password=True`
    eine andere Seite als die Passwort-Ändern-Seite selbst aufruft."""


class PermissionDeniedError(HTTPException):
    def __init__(self, detail: str = "Keine Berechtigung für diese Aktion") -> None:
        super().__init__(status_code=403, detail=detail)


class CSRFError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=403, detail="Ungültiges oder fehlendes CSRF-Token")


# Pfade, die auch mit `must_change_password=True` erreichbar bleiben
# müssen (sonst könnte sich der Nutzer nie ein neues Passwort setzen).
_PASSWORD_CHANGE_EXEMPT_PATHS = frozenset(
    {"/dashboard/change-password", "/dashboard/logout"}
)


def _load_user_from_session(request: Request, db: Session, settings: Settings) -> User | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    payload = read_session_token(token, settings)
    if payload is None:
        return None
    user = db.get(User, payload["user_id"])
    if user is None or not user.is_active:
        return None
    request.state.csrf_token = payload["csrf"]
    request.state.user = user
    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User | None:
    """Für Stellen, die den Nutzer OHNE Zwang zur Anmeldung kennen wollen
    (z. B. die Login-Seite selbst, um bereits angemeldete Nutzer
    weiterzuleiten)."""
    return _load_user_from_session(request, db, settings)


def require_login(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Basis-Dependency für JEDE Dashboard-Seite (auch rein lesende) -
    alle drei Rollen dürfen lesen (siehe Rechte-Matrix), daher hier KEINE
    zusätzliche Rollenprüfung, nur "ist überhaupt angemeldet"."""
    user = _load_user_from_session(request, db, settings)
    if user is None:
        raise NotAuthenticatedError(next_path=str(request.url.path))
    if user.must_change_password and request.url.path not in _PASSWORD_CHANGE_EXEMPT_PATHS:
        raise ForcePasswordChangeError()
    return user


def require_api_login(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Wie `require_login`, aber für die JSON-API (`/api/...`) - liefert
    bei fehlender Anmeldung einen 401 JSON-Fehler statt eines
    Redirects (ein JSON-Client kann mit einem Redirect nichts anfangen)."""
    user = _load_user_from_session(request, db, settings)
    if user is None:
        raise HTTPException(status_code=401, detail="Nicht angemeldet")
    return user


def verify_csrf_token(request: Request, csrf_token: str) -> None:
    expected = getattr(request.state, "csrf_token", None)
    if not expected or not csrf_token or csrf_token != expected:
        raise CSRFError()


def require_role(*allowed_roles: str, permission: str | None = None):
    """Dependency-Factory für zustandsverändernde (POST) Dashboard-Routen:
    prüft IN DIESER REIHENFOLGE Login -> CSRF -> Berechtigung. Wird direkt
    als `Depends(require_role(...))` in der Router-Funktionssignatur
    verwendet - das ist die serverseitige Durchsetzung, unabhängig davon,
    ob ein Formular-Button im UI sichtbar war oder nicht.

    `allowed_roles`: optionale explizite Rollen-Allowlist (Rollenname
    klein geschrieben, z. B. "admin"). `permission`: optionaler Abgleich
    gegen PERMISSION_MATRIX - i. d. R. NUR `permission` verwenden (nicht
    beides), `allowed_roles` existiert für den Sonderfall Nutzerverwaltung
    (dort ist "nur admin" einfacher direkt als Rollenname auszudrücken).
    """

    def dependency(
        request: Request,
        csrf_token: str = Form(...),
        db: Session = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ) -> User:
        user = _load_user_from_session(request, db, settings)
        if user is None:
            raise NotAuthenticatedError(next_path=str(request.url.path))
        if user.must_change_password:
            raise ForcePasswordChangeError()
        verify_csrf_token(request, csrf_token)

        if permission is not None and not has_permission(user, permission):
            raise PermissionDeniedError()
        if allowed_roles:
            role_name = user.role.name.strip().lower() if user.role else ""
            if role_name not in {r.lower() for r in allowed_roles}:
                raise PermissionDeniedError()
        return user

    return dependency
