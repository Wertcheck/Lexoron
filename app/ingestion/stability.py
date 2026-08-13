"""Hilfsfunktionen fuer den Intake: Hashing und Schreibvorgang-Stabilität.

Wichtig (Konzept Prompt 05): Dateien duerfen erst verarbeitet werden, wenn
der Schreibvorgang abgeschlossen ist - sonst droht das Kopieren/Hashen
einer unvollstaendigen Datei (z. B. bei langsamen Netzlaufwerken/Scannern).
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path


def compute_sha256(path: Path, chunk_size: int = 65536) -> str:
    """Berechnet den SHA-256-Hash einer Datei, ohne sie komplett in den
    Speicher zu laden (wichtig bei groesseren Scans/PDFs)."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def wait_until_stable(
    path: Path,
    *,
    checks: int = 2,
    interval_seconds: float = 0.5,
    timeout_seconds: float = 30.0,
) -> bool:
    """Wartet, bis sich die Dateigröße über `checks` aufeinanderfolgende
    Prüfungen hinweg nicht mehr ändert - ein einfacher, robuster Indikator
    dafür, dass ein Schreibvorgang abgeschlossen ist.

    Gibt True zurück, sobald die Datei stabil ist. Gibt False zurück, wenn
    `timeout_seconds` überschritten wird (z. B. bei einer sehr langsam
    geschriebenen Datei) oder die Datei zwischenzeitlich verschwindet.
    """
    deadline = time.monotonic() + timeout_seconds
    last_size = -1
    stable_count = 0

    while time.monotonic() < deadline:
        if not path.exists():
            return False
        current_size = path.stat().st_size
        if current_size == last_size:
            stable_count += 1
            if stable_count >= checks:
                return True
        else:
            stable_count = 0
        last_size = current_size
        time.sleep(interval_seconds)

    return False
