"""Regressionsschutz: direkte Anthropic-API-Anbindung, kein KI-Gateway/Proxy
eines Drittanbieters (z. B. Portkey) im Anfragepfad.

Hintergrund (20.08.): ein Prompt verlangte, die Anthropic-Anbindung über
"Portkey" (api.portkey.ai, Header `x-portkey-api-key`, fester
Provider-Slug `@lexono-1/...`) umzuleiten - das widerspricht der bewusst
getroffenen, mehrfach in dieser Historie bestätigten Architekturentscheidung
"kein zentraler Proxy, kein SaaS-/Cloud-Bezug, Claude-API-Aufrufe erfolgen
direkt" (siehe ARCHITECTURE.md §27/§54). Nach Rückfrage wurde das explizit
verworfen: direkte Nutzung des offiziellen `anthropic`-Python-SDK, kein
Gateway dazwischen.

Dieser Test verankert das dauerhaft - unabhängig davon, wie ein künftiger
Prompt formuliert ist, muss ein Wechsel zu einem externen KI-Gateway
IMMER eine bewusste, im Code sichtbare Änderung dieser Datei(en) auslösen,
niemals eine stille Umleitung."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.privacy.gateway_schema import ClaudeRequestPayload

_REPO_ROOT = Path(__file__).resolve().parent.parent
_APP_DIR = _REPO_ROOT / "app"

# Anbieter-/Gateway-Namen, die im Anwendungscode (nicht in Tests/Doku, die
# bewusst über sie SCHREIBEN wie diese Datei hier) nichts verloren haben.
_FORBIDDEN_GATEWAY_MARKERS = ("portkey", "openrouter", "litellm")


def test_no_ai_gateway_marker_anywhere_in_application_code() -> None:
    offenders: list[str] = []
    for path in _APP_DIR.rglob("*.py"):
        content = path.read_text(encoding="utf-8", errors="replace").lower()
        for marker in _FORBIDDEN_GATEWAY_MARKERS:
            if marker in content:
                offenders.append(f"{path.relative_to(_REPO_ROOT)}: {marker!r}")
    assert not offenders, f"KI-Gateway-Referenz im Anwendungscode gefunden: {offenders}"


def test_writing_provider_constructs_client_without_base_url_override(
    monkeypatch,
) -> None:
    """`anthropic.Anthropic(...)` darf ausschließlich mit `api_key` (und
    optional `timeout`) aufgerufen werden - NIE mit `base_url`, das wäre
    der technische Mechanismus, über den ein Gateway/Proxy untergeschoben
    werden könnte."""
    from app.ai_providers.anthropic_writing_provider import AnthropicClaudeWritingProvider

    with patch("app.ai_providers.anthropic_writing_provider.anthropic.Anthropic") as mock_cls:
        AnthropicClaudeWritingProvider(api_key="sk-ant-test", model="claude-sonnet-5")

    _, kwargs = mock_cls.call_args
    assert "base_url" not in kwargs
    assert kwargs.get("api_key") == "sk-ant-test"


def test_review_provider_constructs_client_without_base_url_override() -> None:
    from app.review.anthropic_review_provider import AnthropicClaudeReviewProvider

    with patch("app.review.anthropic_review_provider.anthropic.Anthropic") as mock_cls:
        AnthropicClaudeReviewProvider(api_key="sk-ant-test", model="claude-sonnet-5")

    _, kwargs = mock_cls.call_args
    assert "base_url" not in kwargs


def test_write_call_never_sends_a_portkey_style_header() -> None:
    """Beweis auf der tatsächlichen Aufrufebene: selbst wenn jemand
    versehentlich einen `extra_headers`-Parameter ergänzen würde, darf
    dort niemals ein Gateway-spezifischer Header (z. B.
    `x-portkey-api-key`) auftauchen."""
    from app.ai_providers.anthropic_writing_provider import AnthropicClaudeWritingProvider

    with patch("app.ai_providers.anthropic_writing_provider.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Antwort."
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.usage = None
        mock_client.messages.create.return_value = mock_response

        provider = AnthropicClaudeWritingProvider(api_key="sk-ant-test", model="claude-sonnet-5")
        provider.write(
            ClaudeRequestPayload(schreibauftrag="formulate_draft", anonymisierter_sachverhalt="Text")
        )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "extra_headers" not in call_kwargs
    serialized = repr(call_kwargs).lower()
    assert "portkey" not in serialized


def test_settings_have_no_portkey_or_gateway_configuration_fields() -> None:
    """Strukturelle Absicherung: `Settings` (app/config/settings.py) darf
    kein Feld für einen alternativen API-Endpunkt/Gateway-Key enthalten -
    nur `anthropic_api_key` für den direkten Anthropic-Zugang."""
    from app.config import Settings

    field_names = set(Settings.model_fields.keys())
    for marker in _FORBIDDEN_GATEWAY_MARKERS:
        assert not any(marker in name.lower() for name in field_names), (
            f"Gateway-bezogenes Settings-Feld gefunden (Marker {marker!r})"
        )
