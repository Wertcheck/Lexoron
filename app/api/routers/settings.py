"""Einstellungen-Endpunkt (Prompt 21).

KRITISCH: `Settings` enthaelt `SecretStr`-Felder (`mail_password`,
`anthropic_api_key`). Dieser Router referenziert diese Felder an keiner
Stelle - `SettingsOut` wird explizit Feld fuer Feld aus dem
`Settings`-Objekt zusammengebaut (siehe `SettingsOut.from_settings` in
app/api/schemas.py - seit Schritt 3 die EINZIGE Konstruktionsstelle dieser
Allowlist, auch genutzt vom Backup-Snapshot, app/backup/service.py).
Dadurch kann ein zukuenftig ergaenztes Secret-Feld nicht versehentlich
ueber diesen Endpunkt exponiert werden, selbst wenn `SettingsOut`
vergessen wuerde zu aktualisieren - ein neues Feld erscheint schlicht
nicht in der Antwort, bis es hier bewusst ergaenzt wird.

Abgesichert per Test (`tests/test_api.py`): der Response-Body enthaelt
nachweislich weder den Wert von `mail_password` noch von
`anthropic_api_key`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.schemas import SettingsOut
from app.config import Settings, get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_current_settings(settings: Settings = Depends(get_settings)) -> SettingsOut:
    return SettingsOut.from_settings(settings)
