"""Tests für den stummen Local-AI-Statuscheck beim Anwendungsstart
(app/main.py: `_run_silent_local_ai_check`) - verbindet die bereits
bestehende `LocalAiSetupService`/`OllamaInstaller`-Logik (§68) mit dem
tatsächlichen FastAPI-Lifespan, analog zu `_run_silent_update_check`.

WICHTIG: Kein Test ruft je einen echten Ollama-Prozess/HTTP-Aufruf auf.
`LocalAiSetupService` und der Provider werden durch Fakes ersetzt (gleiches
Muster wie tests/test_local_ai_setup_orchestrator.py) - dieser Task fügt
KEINE neue Status-/Startlogik hinzu, er verkabelt nur die bestehende, daher
werden hier auch keine neuen `LocalAiState`-Übergänge geprüft (das leistet
bereits tests/test_local_ai_setup_orchestrator.py), sondern ausschließlich:
wird die bestehende Logik in der richtigen Reihenfolge aufgerufen, und
verändert sie den bestehenden App-Start nicht."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as main_module
from app.local_ai.setup_orchestrator import LocalAiState, LocalAiStatus
from app.main import _run_silent_local_ai_check, app


class _FakeApp:
    def __init__(self) -> None:
        self.state = SimpleNamespace()


class _FakeOllamaInstaller:
    def __init__(self, *, ensure_running_result: bool = True) -> None:
        self.ensure_running_calls: list[dict] = []
        self.ensure_running_result = ensure_running_result

    def ensure_running(self, *, is_reachable, **kwargs) -> bool:
        self.ensure_running_calls.append({"is_reachable": is_reachable, **kwargs})
        return self.ensure_running_result


class _FakeService:
    """Liefert der Reihe nach die übergebenen Status - ein Aufruf pro
    Listenelement, der letzte Wert bleibt bei weiteren Aufrufen stehen."""

    def __init__(
        self, statuses: list[LocalAiStatus], *, ensure_running_result: bool = True
    ) -> None:
        self._statuses = list(statuses)
        self.get_status_calls = 0
        self.ollama_installer = _FakeOllamaInstaller(ensure_running_result=ensure_running_result)

    def get_status(self, settings=None) -> LocalAiStatus:
        self.get_status_calls += 1
        index = min(self.get_status_calls - 1, len(self._statuses) - 1)
        return self._statuses[index]


def _run_check(service: _FakeService, *, provider=None, monkeypatch) -> _FakeApp:
    monkeypatch.setattr(main_module, "LocalAiSetupService", lambda: service)
    monkeypatch.setattr(main_module, "build_local_llm_provider", lambda settings: provider)
    fake_app = _FakeApp()
    asyncio.run(_run_silent_local_ai_check(fake_app, settings=object()))
    return fake_app


class _FakeProvider:
    def __init__(self, *, reachable: bool) -> None:
        self.reachable = reachable

    def check_health(self):
        return SimpleNamespace(reachable=self.reachable)


def test_disabled_triggers_no_start_action(monkeypatch) -> None:
    """1. LOCAL_AI_ENABLED=false -> keine Local-AI-Startaktion."""
    status = LocalAiStatus(state=LocalAiState.DISABLED, configured_model=None)
    service = _FakeService([status])

    fake_app = _run_check(service, monkeypatch=monkeypatch)

    assert service.ollama_installer.ensure_running_calls == []
    assert fake_app.state.local_ai_status.state == LocalAiState.DISABLED


def test_already_ready_does_not_trigger_restart(monkeypatch) -> None:
    """2. Local AI bereits READY -> kein unnötiger Restart."""
    status = LocalAiStatus(state=LocalAiState.READY, configured_model="qwen3:4b")
    service = _FakeService([status])

    fake_app = _run_check(service, monkeypatch=monkeypatch)

    assert service.ollama_installer.ensure_running_calls == []
    assert service.get_status_calls == 1
    assert fake_app.state.local_ai_status.state == LocalAiState.READY


def test_runtime_unreachable_uses_existing_ensure_running_logic(monkeypatch) -> None:
    """3. Runtime vorhanden, aber nicht erreichbar -> vorhandene
    ensure_running()-Logik wird verwendet."""
    unreachable = LocalAiStatus(
        state=LocalAiState.RUNTIME_UNREACHABLE, configured_model="qwen3:4b"
    )
    service = _FakeService([unreachable, unreachable])
    provider = _FakeProvider(reachable=False)

    _run_check(service, provider=provider, monkeypatch=monkeypatch)

    assert len(service.ollama_installer.ensure_running_calls) == 1
    assert service.get_status_calls == 2


def test_successful_start_reaches_ready(monkeypatch) -> None:
    """4. Start erfolgreich -> READY."""
    unreachable = LocalAiStatus(
        state=LocalAiState.RUNTIME_UNREACHABLE, configured_model="qwen3:4b"
    )
    ready = LocalAiStatus(state=LocalAiState.READY, configured_model="qwen3:4b")
    service = _FakeService([unreachable, ready], ensure_running_result=True)
    provider = _FakeProvider(reachable=True)

    fake_app = _run_check(service, provider=provider, monkeypatch=monkeypatch)

    assert fake_app.state.local_ai_status.state == LocalAiState.READY


def test_failed_start_keeps_correct_error_status_not_ready(monkeypatch) -> None:
    """5. Start schlägt fehl -> korrekter Fehlerstatus (kein READY);
    7. es entsteht dabei niemals ein falscher READY-Status, selbst wenn
    ensure_running() `True` zurückmeldet - der Endzustand kommt IMMER aus
    dem erneuten get_status()-Aufruf, nie aus dem ensure_running()-
    Rückgabewert."""
    unreachable = LocalAiStatus(
        state=LocalAiState.RUNTIME_UNREACHABLE, configured_model="qwen3:4b"
    )
    service = _FakeService([unreachable, unreachable], ensure_running_result=True)
    provider = _FakeProvider(reachable=False)

    fake_app = _run_check(service, provider=provider, monkeypatch=monkeypatch)

    assert fake_app.state.local_ai_status.state == LocalAiState.RUNTIME_UNREACHABLE
    assert fake_app.state.local_ai_status.state != LocalAiState.READY


def test_model_missing_is_reported_without_restart_attempt(monkeypatch) -> None:
    """6. Modell fehlt -> MODEL_MISSING, kein Neustartversuch (ein
    Neustart der Runtime würde am fehlenden Modell nichts ändern - Modell-
    Download bleibt Aufgabe des separaten Setup-Assistenten, §68)."""
    status = LocalAiStatus(state=LocalAiState.MODEL_MISSING, configured_model="qwen3:4b")
    service = _FakeService([status])

    fake_app = _run_check(service, monkeypatch=monkeypatch)

    assert service.ollama_installer.ensure_running_calls == []
    assert fake_app.state.local_ai_status.state == LocalAiState.MODEL_MISSING


def test_runtime_missing_is_reported_without_restart_attempt(monkeypatch) -> None:
    """RUNTIME_MISSING (gar nicht installiert) darf ebenfalls keinen
    ensure_running()-Versuch auslösen - das ist kein "kurz nicht
    erreichbar"-Fall, sondern "gar nicht installiert"."""
    status = LocalAiStatus(state=LocalAiState.RUNTIME_MISSING, configured_model="qwen3:4b")
    service = _FakeService([status])

    fake_app = _run_check(service, monkeypatch=monkeypatch)

    assert service.ollama_installer.ensure_running_calls == []
    assert fake_app.state.local_ai_status.state == LocalAiState.RUNTIME_MISSING


def test_app_startup_stays_functional_when_local_ai_check_runs(monkeypatch) -> None:
    """8. Der bestehende Anwendungsstart bleibt funktionsfähig - /health
    antwortet weiterhin normal, während der Local-AI-Check im Hintergrund
    läuft (kein echter Netzwerkaufruf, Service/Provider sind Fakes)."""
    unreachable = LocalAiStatus(
        state=LocalAiState.RUNTIME_UNREACHABLE, configured_model="qwen3:4b"
    )
    service = _FakeService([unreachable, unreachable], ensure_running_result=False)
    provider = _FakeProvider(reachable=False)

    monkeypatch.setattr(main_module, "LocalAiSetupService", lambda: service)
    monkeypatch.setattr(main_module, "build_local_llm_provider", lambda settings: provider)

    with TestClient(app) as startup_client:
        response = startup_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
