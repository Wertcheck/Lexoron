"""Test fuer app/ingestion/watcher.py (Prompt 05).

Echter End-to-End-Test mit tatsaechlichen Dateisystem-Events (nicht nur
gemockt), da genau das Verhalten ist, das im produktiven Einsatz zaehlt.
Nutzt grosszuegige Timeouts, um auf langsameren/virtualisierten
Dateisystemen robust zu bleiben.
"""

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ingestion.intake import IntakeService
from app.ingestion.watcher import IntakeWatcher
from app.models import Document
from app.models.base import Base


@pytest.fixture()
def session_factory(tmp_path: Path):
    db_path = tmp_path / "watcher_test.db"
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_watcher_detects_and_ingests_new_file(
    tmp_path: Path, session_factory
) -> None:
    watched_dir = tmp_path / "eingang"
    watched_dir.mkdir()
    storage_dir = tmp_path / "intake_storage"

    intake_service = IntakeService(storage_dir)
    ingested: list[Document] = []

    watcher = IntakeWatcher(
        watched_folders=[str(watched_dir)],
        intake_service=intake_service,
        session_factory=session_factory,
        on_ingested=lambda doc: ingested.append(doc),
    )
    watcher.start()
    try:
        time.sleep(0.3)  # Observer-Startzeit
        new_file = watched_dir / "neue_datei.pdf"
        new_file.write_bytes(b"Synthetischer Testinhalt fuer Watcher-Test")

        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and not ingested:
            time.sleep(0.1)
    finally:
        watcher.stop()

    assert len(ingested) == 1
    document = ingested[0]
    assert document.original_filename == "neue_datei.pdf"
    assert Path(document.file_path).exists()
    assert Path(document.file_path).parent == storage_dir


def test_watcher_skips_nonexistent_folder_without_crashing(
    tmp_path: Path, session_factory
) -> None:
    """Ein nicht existierender Ordner (z. B. Netzlaufwerk kurz nicht
    erreichbar) darf die Ueberwachung nicht zum Absturz bringen."""
    intake_service = IntakeService(tmp_path / "intake_storage")

    watcher = IntakeWatcher(
        watched_folders=[str(tmp_path / "existiert_nicht")],
        intake_service=intake_service,
        session_factory=session_factory,
    )
    # Darf keine Exception werfen.
    watcher.start()
    watcher.stop()
