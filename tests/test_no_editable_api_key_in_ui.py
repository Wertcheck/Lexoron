"""Regressionsschutz für Schritt 3, Punkt 1 (API-Sicherheit):

'Blende etwaige API-Key-Eingabefelder in den UI-Einstellungen für
Endnutzer aus.' Bestandsaufnahme ergab: es gibt im gesamten Dashboard
keinen einzigen Endpunkt, der `.env`-Werte (insbesondere
`anthropic_api_key`) überhaupt schreibbar macht - Konfiguration erfolgt
ausschließlich dateibasiert (siehe ARCHITECTURE.md, "kein SaaS-/Cloud-
Bezug", Settings sind SecretStr + Allowlist-Schemas, siehe
app/api/schemas.py: SettingsOut, app/web/account_router.py:
account_privacy). Dieser Test verankert das dauerhaft: kein Template darf
ein Formularfeld einführen, dessen `name`-Attribut auf einen der
Settings-Secret-Felder verweist - ein zukünftiger Editier-Endpunkt für den
API-Key würde diesen Test sofort brechen.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.web.template_paths import TEMPLATES_DIR

_FORBIDDEN_FIELD_NAMES = ("anthropic_api_key", "api_key", "mail_password")
_INPUT_NAME_PATTERN = re.compile(
    r'<(?:input|textarea|select)\b[^>]*\bname="([^"]+)"', re.IGNORECASE
)


def test_no_template_contains_an_editable_secret_field() -> None:
    offenders: list[str] = []
    for path in Path(TEMPLATES_DIR).rglob("*.html"):
        content = path.read_text(encoding="utf-8")
        for field_name in _INPUT_NAME_PATTERN.findall(content):
            if field_name.strip().lower() in _FORBIDDEN_FIELD_NAMES:
                offenders.append(f"{path.name}: name={field_name!r}")
    assert not offenders, f"Editierbares Secret-Feld im UI gefunden: {offenders}"


def test_settings_allowlist_schema_excludes_secrets() -> None:
    """Zweite, vom Template unabhängige Absicherung: das API-Response-
    Schema selbst kann `anthropic_api_key`/`mail_password` strukturell gar
    nicht enthalten (siehe app/api/schemas.py: SettingsOut)."""
    from app.api.schemas import SettingsOut

    field_names = set(SettingsOut.model_fields.keys())
    assert "anthropic_api_key" not in field_names
    assert "mail_password" not in field_names
