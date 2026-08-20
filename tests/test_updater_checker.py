"""Tests für app/updater/checker.py (Schritt 3)."""

from __future__ import annotations

import httpx
import pytest

from app.updater.checker import UpdateCheckResult, check_for_update


def test_disabled_by_default_when_no_manifest_url() -> None:
    result = check_for_update(None)
    assert result == UpdateCheckResult(checked=False, update_available=False)


def test_reports_no_update_when_versions_match(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float) -> httpx.Response:
        return httpx.Response(200, json={"version": "0.1.0"}, request=httpx.Request("GET", url))

    monkeypatch.setattr("app.updater.checker.httpx.get", fake_get)
    result = check_for_update("https://example.invalid/version.json", current_version="0.1.0")

    assert result.checked is True
    assert result.update_available is False


def test_detects_newer_version(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float) -> httpx.Response:
        return httpx.Response(
            200,
            json={"version": "0.2.0", "download_url": "https://example.invalid/setup.exe"},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr("app.updater.checker.httpx.get", fake_get)
    result = check_for_update("https://example.invalid/version.json", current_version="0.1.0")

    assert result.checked is True
    assert result.update_available is True
    assert result.latest_version == "0.2.0"
    assert result.download_url == "https://example.invalid/setup.exe"


def test_older_or_equal_remote_version_is_not_an_update(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float) -> httpx.Response:
        return httpx.Response(200, json={"version": "0.0.9"}, request=httpx.Request("GET", url))

    monkeypatch.setattr("app.updater.checker.httpx.get", fake_get)
    result = check_for_update("https://example.invalid/version.json", current_version="0.1.0")

    assert result.update_available is False


def test_network_error_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float) -> httpx.Response:
        raise httpx.ConnectError("kein Netzwerk")

    monkeypatch.setattr("app.updater.checker.httpx.get", fake_get)
    result = check_for_update("https://example.invalid/version.json")

    assert result.checked is False
    assert result.update_available is False
    assert result.error is not None


def test_invalid_json_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float) -> httpx.Response:
        return httpx.Response(200, content=b"nicht valides json", request=httpx.Request("GET", url))

    monkeypatch.setattr("app.updater.checker.httpx.get", fake_get)
    result = check_for_update("https://example.invalid/version.json")

    assert result.checked is False
    assert result.error is not None


def test_missing_version_field_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float) -> httpx.Response:
        return httpx.Response(200, json={"download_url": "x"}, request=httpx.Request("GET", url))

    monkeypatch.setattr("app.updater.checker.httpx.get", fake_get)
    result = check_for_update("https://example.invalid/version.json")

    assert result.checked is False
    assert result.update_available is False


def test_http_error_status_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float) -> httpx.Response:
        return httpx.Response(500, request=httpx.Request("GET", url))

    monkeypatch.setattr("app.updater.checker.httpx.get", fake_get)
    result = check_for_update("https://example.invalid/version.json")

    assert result.checked is False
    assert result.error is not None
