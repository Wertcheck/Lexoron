"""Tests für app/ollama_setup/service.py (20.08., "Ollama-Installer-/
Update-Assistent").

WICHTIG: Kein Test ruft je `_default_download`/`_default_launch_elevated`
auf - alle Netzwerk-/OS-Aufrufe werden durch Fakes ersetzt (gleiches Muster
wie tests/test_setup_wizard.py für app/setup/wizard.py: run_setup_wizard).
Es findet in dieser Testdatei nie ein echter Download oder eine echte
UAC-Elevation statt."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from app.ollama_setup.service import (
    OLLAMA_WINDOWS_INSTALLER_URL,
    STATUS_DONE,
    STATUS_DOWNLOADING,
    STATUS_ERROR,
    STATUS_LAUNCHING,
    STATUS_WAITING,
    OllamaInstallerService,
    OllamaInstallProgress,
)


def test_default_download_url_is_the_official_https_ollama_domain() -> None:
    """Nur die Konstante wird geprüft - die zugehörige Default-Funktion
    wird NIE aufgerufen (siehe Moduldocstring dieser Datei)."""
    assert OLLAMA_WINDOWS_INSTALLER_URL == "https://ollama.com/download/OllamaSetup.exe"
    assert OLLAMA_WINDOWS_INSTALLER_URL.startswith("https://")


class _FakeDownloader:
    def __init__(self, *, chunks: list[tuple[int, int]] | None = None) -> None:
        self.calls: list[tuple[str, Path]] = []
        self.chunks = chunks or [(50, 100), (100, 100)]

    def __call__(self, url, dest_path, on_chunk) -> None:  # noqa: ANN001
        self.calls.append((url, dest_path))
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(b"fake-installer-bytes")
        for downloaded, total in self.chunks:
            on_chunk(downloaded, total)


def _collect_progress() -> tuple[list[OllamaInstallProgress], Callable[[OllamaInstallProgress], None]]:
    events: list[OllamaInstallProgress] = []

    def on_progress(progress: OllamaInstallProgress) -> None:
        events.append(progress)

    return events, on_progress


def test_successful_run_reaches_done_status(tmp_path: Path) -> None:
    downloader = _FakeDownloader()
    service = OllamaInstallerService(
        download_fn=downloader,
        launch_elevated_fn=lambda path: True,
        check_reachable_fn=lambda: True,
        staging_dir=tmp_path,
        reachability_poll_attempts=3,
        reachability_poll_interval_seconds=0,
    )
    events, on_progress = _collect_progress()

    result = service.run_guided_install(on_progress)

    assert result.status == STATUS_DONE
    assert result.percent == 100
    assert downloader.calls == [(OLLAMA_WINDOWS_INSTALLER_URL, tmp_path / "OllamaSetup.exe")]
    statuses = [e.status for e in events]
    assert statuses[0] == STATUS_DOWNLOADING
    assert STATUS_LAUNCHING in statuses
    assert STATUS_WAITING in statuses
    assert statuses[-1] == STATUS_DONE


def test_download_progress_percent_is_reported(tmp_path: Path) -> None:
    downloader = _FakeDownloader(chunks=[(25, 100), (75, 100), (100, 100)])
    service = OllamaInstallerService(
        download_fn=downloader,
        launch_elevated_fn=lambda path: True,
        check_reachable_fn=lambda: True,
        staging_dir=tmp_path,
        reachability_poll_attempts=1,
        reachability_poll_interval_seconds=0,
    )
    events, on_progress = _collect_progress()

    service.run_guided_install(on_progress)

    download_events = [e for e in events if e.status == STATUS_DOWNLOADING]
    percents = [e.percent for e in download_events]
    assert percents == [0, 25, 75, 100]


def test_declined_elevation_results_in_error(tmp_path: Path) -> None:
    service = OllamaInstallerService(
        download_fn=_FakeDownloader(),
        launch_elevated_fn=lambda path: False,  # Nutzer lehnt UAC ab
        check_reachable_fn=lambda: True,
        staging_dir=tmp_path,
    )
    events, on_progress = _collect_progress()

    result = service.run_guided_install(on_progress)

    assert result.status == STATUS_ERROR
    assert result.error is not None
    assert "bestätigt" in result.error
    # check_reachable_fn darf nach abgelehnter Elevation nicht mehr aufgerufen werden.
    assert STATUS_WAITING not in [e.status for e in events]


def test_reachability_timeout_results_in_error_not_infinite_wait(tmp_path: Path) -> None:
    service = OllamaInstallerService(
        download_fn=_FakeDownloader(),
        launch_elevated_fn=lambda path: True,
        check_reachable_fn=lambda: False,  # Ollama wird nie erreichbar
        staging_dir=tmp_path,
        reachability_poll_attempts=3,
        reachability_poll_interval_seconds=0,
    )
    events, on_progress = _collect_progress()

    result = service.run_guided_install(on_progress)

    assert result.status == STATUS_ERROR
    assert result.error is not None
    assert "erneut prüfen" in result.error


def test_download_error_is_caught_and_reported(tmp_path: Path) -> None:
    def _raising_downloader(url, dest_path, on_chunk):  # noqa: ANN001
        raise ConnectionError("Netzwerk nicht erreichbar")

    service = OllamaInstallerService(
        download_fn=_raising_downloader,
        launch_elevated_fn=lambda path: True,
        check_reachable_fn=lambda: True,
        staging_dir=tmp_path,
    )
    events, on_progress = _collect_progress()

    result = service.run_guided_install(on_progress)

    assert result.status == STATUS_ERROR
    assert "ConnectionError" in result.error


def test_concurrent_calls_each_return_independent_results(tmp_path: Path) -> None:
    """Kein Nebenläufigkeitsanspruch der Service-Instanz selbst (das
    Verhindern DOPPELTER gleichzeitiger Läufe ist Aufgabe des Aufrufers
    - app/web/monitoring_router.py: _ollama_install_lock) - hier nur
    sichergestellt, dass zwei sequentielle Aufrufe unabhängig funktionieren."""
    service = OllamaInstallerService(
        download_fn=_FakeDownloader(),
        launch_elevated_fn=lambda path: True,
        check_reachable_fn=lambda: True,
        staging_dir=tmp_path,
        reachability_poll_attempts=1,
        reachability_poll_interval_seconds=0,
    )
    _, on_progress = _collect_progress()

    first = service.run_guided_install(on_progress)
    second = service.run_guided_install(on_progress)

    assert first.status == STATUS_DONE
    assert second.status == STATUS_DONE


def test_launch_elevated_raises_on_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.ollama_setup.service as service_module

    monkeypatch.setattr(service_module.os, "name", "posix")
    with pytest.raises(RuntimeError):
        service_module._default_launch_elevated(Path("/tmp/OllamaSetup.exe"))
