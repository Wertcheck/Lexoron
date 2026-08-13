"""Tests fuer app/ingestion/stability.py (Prompt 05)."""

import hashlib
import threading
import time
from pathlib import Path

from app.ingestion.stability import compute_sha256, wait_until_stable


def test_compute_sha256_matches_known_value(tmp_path: Path) -> None:
    file_path = tmp_path / "test.txt"
    content = b"Synthetischer Testinhalt fuer Hash-Berechnung"
    file_path.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()
    assert compute_sha256(file_path) == expected


def test_wait_until_stable_returns_true_for_static_file(tmp_path: Path) -> None:
    file_path = tmp_path / "static.txt"
    file_path.write_bytes(b"unveraendert")

    assert (
        wait_until_stable(
            file_path, checks=2, interval_seconds=0.05, timeout_seconds=2.0
        )
        is True
    )


def test_wait_until_stable_returns_false_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "existiert_nicht.txt"
    assert (
        wait_until_stable(
            missing_path, checks=2, interval_seconds=0.05, timeout_seconds=0.3
        )
        is False
    )


def test_wait_until_stable_waits_for_slow_write_to_finish(tmp_path: Path) -> None:
    """Simuliert eine Datei, die noch waechst - wait_until_stable darf erst
    True liefern, nachdem der (simulierte) Schreibvorgang beendet ist.

    Der Pruefintervall ist bewusst groesser als der Abstand zwischen den
    simulierten Schreibvorgaengen, damit zwischen zwei Pruefungen fast
    immer ein neuer Schreibvorgang liegt - das macht den Test robust gegen
    Timing-Schwankungen statt auf exaktes Timing angewiesen zu sein.
    """
    file_path = tmp_path / "wachsend.txt"
    file_path.write_bytes(b"")
    write_gap_seconds = 0.15
    check_interval_seconds = 0.25  # > write_gap_seconds

    def slow_writer() -> None:
        for i in range(3):
            time.sleep(write_gap_seconds)
            with file_path.open("ab") as f:
                f.write(f"chunk-{i}".encode())

    writer_thread = threading.Thread(target=slow_writer)
    writer_thread.start()

    result = wait_until_stable(
        file_path,
        checks=2,
        interval_seconds=check_interval_seconds,
        timeout_seconds=5.0,
    )
    writer_thread.join()

    assert result is True
    # Datei muss den vollstaendigen Inhalt aller drei Chunks enthalten -
    # sprich: wait_until_stable hat nicht vorzeitig "stabil" gemeldet.
    assert file_path.read_bytes() == b"chunk-0chunk-1chunk-2"
