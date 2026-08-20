"""LogAccessService – admin-only Ansicht/Download der App-Logs (Schritt 3).

GRUNDREGEL (unverändert seit Prompt 32, siehe app/observability/logging_config.py):
Logs sollen bereits durch Entwickler-Disziplin frei von Mandanteninhalten
sein. Diese Funktion ist eine ZUSÄTZLICHE Verteidigungslinie (defense in
depth), kein Ersatz dafür - vor jeder Anzeige/jedem Download läuft der
Log-Inhalt zusätzlich durch denselben Pseudonymizer, der auch reale
Mandanteninhalte vor einem Claude-API-Aufruf schützt (app/privacy/), damit
ein versehentlich eingebetteter Personenname/eine E-Mail-Adresse/IBAN in
einer unerwarteten Exception-Message nicht unredigiert das System
verlässt.

Nur die AKTIVE Log-Datei (`settings.log_file_path`) wird gelesen - bereits
rotierte ältere Generationen (`*.log.1`, `*.log.2`, ...) sind bewusst NICHT
Teil dieser ersten Umsetzung."""

from __future__ import annotations

from pathlib import Path

from app.privacy.pseudonymizer import Pseudonymizer

_DEFAULT_MAX_LINES = 1000


class LogAccessService:
    def __init__(self) -> None:
        self._pseudonymizer = Pseudonymizer()

    def read_tail(
        self, log_file_path: str | None, *, max_lines: int = _DEFAULT_MAX_LINES
    ) -> list[str]:
        """Liefert die letzten `max_lines` Zeilen, bereits anonymisiert.
        Leere Liste, wenn keine Log-Datei konfiguriert ist oder sie noch
        nicht existiert (z. B. direkt nach dem Start)."""
        if not log_file_path:
            return []
        path = Path(log_file_path)
        if not path.exists():
            return []
        raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = raw_lines[-max_lines:]
        return [self._pseudonymizer.pseudonymize(line)[0] for line in tail]

    def anonymized_download_content(self, log_file_path: str | None) -> str | None:
        """Liefert den vollständigen, anonymisierten Inhalt der aktiven
        Log-Datei für den Download. `None`, wenn keine Log-Datei
        konfiguriert ist oder sie nicht existiert."""
        if not log_file_path:
            return None
        path = Path(log_file_path)
        if not path.exists():
            return None
        raw_content = path.read_text(encoding="utf-8", errors="replace")
        anonymized, _mappings = self._pseudonymizer.pseudonymize(raw_content)
        return anonymized
