"""OllamaInstallerService – geführter Download/Installation/Update des
lokalen Ollama-Diensts (20.08., "Installer-/Update-Assistent").

WICHTIGE LEITPLANKE (siehe app/updater/checker.py-Moduldocstring für die
gleichlautende, bereits bestehende Projektentscheidung): "keine
automatische externe Kommunikation ohne explizite Freigabe" (CLAUDE.md-
Grundregel) gilt auch hier uneingeschränkt. Dieser Service wird NIE
automatisch beim App-Start oder im Hintergrund aufgerufen - einzig der
Admin-Klick auf "Ollama installieren"/"Ollama aktualisieren" im Dashboard
(app/web/monitoring_router.py: start_ollama_install) startet ihn. Der
eigentliche Installationsschritt selbst braucht zusätzlich eine ECHTE,
von Windows selbst eingeholte UAC-Bestätigung (`ShellExecuteW(verb="runas")`,
siehe `_default_launch_elevated`) - diese kann von der Anwendung technisch
weder ausgelöst noch unterdrückt werden, sie ist die eigentliche
menschliche Freigabe für die Installation.

Alle Netzwerk-/OS-Aufrufe sind injizierbar (gleiches Muster wie
app/setup/wizard.py: `run_setup_wizard(..., run_migrations: Callable,
create_admin: Callable)`) - Tests ersetzen sie durch Fakes, es findet in
Tests NIE ein echter Download oder eine echte UAC-Elevation statt (siehe
tests/test_ollama_installer_service.py).

Update-Fähigkeit: derselbe Ablauf dient sowohl der Erstinstallation als
auch einem späteren Update - der offizielle Ollama-Windows-Installer
aktualisiert eine bereits vorhandene Installation, wenn er erneut
ausgeführt wird (Ollamas eigener, offiziell unterstützter Update-Weg).
Kein separater Codepfad nötig; der Aufrufer wählt nur die Button-
Beschriftung ("installieren" vs. "aktualisieren") abhängig vom aktuellen
Erreichbarkeitsstatus.
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

#: Offizielle, dauerhaft von Ollama selbst betriebene Download-URL (HTTPS,
#: offizielle Domain) - bewusst FEST verdrahtet, niemals aus einer
#: Nutzereingabe/einem Formularfeld übernommen (verhindert, dass dieser
#: admin-only Endpunkt zu einem beliebigen Datei-Download-/SSRF-Proxy
#: umfunktioniert werden könnte).
OLLAMA_WINDOWS_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"

_STAGING_DIR_NAME = "kanzlei_ai_ollama_setup"

STATUS_IDLE = "idle"
STATUS_DOWNLOADING = "downloading"
STATUS_LAUNCHING = "launching"
STATUS_WAITING = "waiting"
STATUS_DONE = "done"
STATUS_ERROR = "error"


@dataclass(frozen=True)
class OllamaInstallProgress:
    status: str = STATUS_IDLE
    percent: int = 0
    message: str = ""
    error: str | None = None


def _default_download(url: str, dest_path: Path, on_chunk: Callable[[int, int], None]) -> None:
    """Lädt `url` per Streaming-GET nach `dest_path`. Ruft `on_chunk(bytes_
    bisher, bytes_gesamt)` nach jedem Chunk auf - `bytes_gesamt=0`, wenn der
    Server kein `Content-Length` sendet (Aufrufer zeigt dann einen
    unbestimmten statt eines prozentgenauen Fortschritts)."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=30.0, follow_redirects=True) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length") or 0)
        downloaded = 0
        with dest_path.open("wb") as f:
            for chunk in response.iter_bytes(chunk_size=262_144):
                f.write(chunk)
                downloaded += len(chunk)
                on_chunk(downloaded, total)


def _default_launch_elevated(installer_path: Path) -> bool:
    """Startet `installer_path` MIT Elevationsanfrage über die Windows-
    ShellExecute-API (`verb="runas"`) - löst den echten, von dieser
    Anwendung nicht unterdrückbaren UAC-Dialog aus (dieselbe ctypes-Technik
    wie run.py: `_apply_light_title_bar`/`_is_webview2_runtime_available`).
    Gibt `False` zurück, wenn der Nutzer die Elevation ablehnt oder ein
    Fehler auftritt (`ShellExecuteW` liefert dann laut Win32-Dokumentation
    einen Wert ≤ 32) - bewusst KEINE Exception für diesen Fall: eine
    Ablehnung ist eine gültige Nutzerentscheidung, kein Programmfehler."""
    if os.name != "nt":
        raise RuntimeError("Elevierter Installationsstart ist nur unter Windows möglich.")

    import ctypes

    result = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
        None, "runas", str(installer_path), None, str(installer_path.parent), 1
    )
    return int(result) > 32


def _default_check_reachable() -> bool:
    from app.config import get_settings
    from app.system_health import SystemHealthService

    settings = get_settings()
    return SystemHealthService().check_ollama_reachability(settings.ollama_base_url).reachable


class OllamaInstallerService:
    def __init__(
        self,
        *,
        download_fn: Callable[[str, Path, Callable[[int, int], None]], None] | None = None,
        launch_elevated_fn: Callable[[Path], bool] | None = None,
        check_reachable_fn: Callable[[], bool] | None = None,
        download_url: str = OLLAMA_WINDOWS_INSTALLER_URL,
        staging_dir: Path | None = None,
        reachability_poll_attempts: int = 20,
        reachability_poll_interval_seconds: float = 3.0,
    ) -> None:
        self._download_fn = download_fn or _default_download
        self._launch_elevated_fn = launch_elevated_fn or _default_launch_elevated
        self._check_reachable_fn = check_reachable_fn or _default_check_reachable
        self._download_url = download_url
        self._staging_dir = staging_dir or (Path(tempfile.gettempdir()) / _STAGING_DIR_NAME)
        self._reachability_poll_attempts = reachability_poll_attempts
        self._reachability_poll_interval_seconds = reachability_poll_interval_seconds

    def run_guided_install(
        self, on_progress: Callable[[OllamaInstallProgress], None]
    ) -> OllamaInstallProgress:
        """Führt den vollständigen Ablauf SYNCHRON aus - der Aufrufer
        (app/web/monitoring_router.py: start_ollama_install) startet dies in
        einem eigenen Hintergrund-Thread, damit der auslösende HTTP-Request
        selbst nicht blockiert. Gibt IMMER den Endzustand zurück, wirft NIE
        - jeder Fehler (Netzwerk, Elevation abgelehnt, Timeout beim Warten
        auf Erreichbarkeit) endet als `status=STATUS_ERROR` mit einer
        verständlichen `error`-Meldung statt eines unbehandelten Absturzes
        im Hintergrund-Thread."""
        try:
            installer_path = self._staging_dir / "OllamaSetup.exe"

            on_progress(
                OllamaInstallProgress(
                    status=STATUS_DOWNLOADING,
                    percent=0,
                    message="Ollama-Setup wird heruntergeladen…",
                )
            )

            def _report_download(downloaded: int, total: int) -> None:
                percent = int(downloaded / total * 100) if total else 0
                size_text = f"{downloaded // 1024} KB"
                if total:
                    size_text += f" von {total // 1024} KB"
                on_progress(
                    OllamaInstallProgress(
                        status=STATUS_DOWNLOADING, percent=percent, message=size_text
                    )
                )

            self._download_fn(self._download_url, installer_path, _report_download)

            on_progress(
                OllamaInstallProgress(
                    status=STATUS_LAUNCHING,
                    percent=100,
                    message="Installation wird gestartet - bitte die Windows-"
                    "Sicherheitsabfrage bestätigen.",
                )
            )
            if not self._launch_elevated_fn(installer_path):
                return self._finish(
                    on_progress,
                    OllamaInstallProgress(
                        status=STATUS_ERROR,
                        percent=100,
                        error="Installation wurde nicht bestätigt oder konnte nicht "
                        "gestartet werden.",
                    ),
                )

            on_progress(
                OllamaInstallProgress(
                    status=STATUS_WAITING,
                    percent=100,
                    message="Installation läuft - warte auf den Ollama-Dienst…",
                )
            )
            for _ in range(self._reachability_poll_attempts):
                if self._check_reachable_fn():
                    return self._finish(
                        on_progress,
                        OllamaInstallProgress(
                            status=STATUS_DONE, percent=100, message="Ollama ist erreichbar."
                        ),
                    )
                time.sleep(self._reachability_poll_interval_seconds)

            return self._finish(
                on_progress,
                OllamaInstallProgress(
                    status=STATUS_ERROR,
                    percent=100,
                    error="Ollama ist nach der Installation noch nicht erreichbar. "
                    "Die Installation läuft möglicherweise noch - bitte in Kürze "
                    "erneut prüfen.",
                ),
            )
        except Exception as exc:  # noqa: BLE001 - darf den Hintergrund-Thread nie unkontrolliert beenden
            logger.warning("Ollama-Installation fehlgeschlagen: %s", exc)
            return self._finish(
                on_progress,
                OllamaInstallProgress(
                    status=STATUS_ERROR, percent=0, error=f"{type(exc).__name__}: {exc}"
                ),
            )

    def _finish(
        self,
        on_progress: Callable[[OllamaInstallProgress], None],
        result: OllamaInstallProgress,
    ) -> OllamaInstallProgress:
        on_progress(result)
        return result
