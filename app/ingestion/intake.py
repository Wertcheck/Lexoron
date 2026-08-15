"""IntakeService – sicheres Erfassen neuer Eingangsdateien.

Ablauf pro Datei (Konzept §3, Schritt 1-2 "Eingang"/"Quarantäne/Intake"):
1. Warten, bis der Schreibvorgang abgeschlossen ist (`wait_until_stable`).
2. Hash berechnen.
3. Datei unveraendert in den kontrollierten Intake-Bereich kopieren
   (niemals verschieben/loeschen aus dem Quellordner - der Anwalt/Scanner
   bleibt Eigentuemer des Originalordners).
4. `Document`-Metadatensatz anlegen (Original vs. Metadaten strikt
   getrennt, siehe app/models/document.py).

Enthaelt bewusst KEINE inhaltliche Verarbeitung (Text/OCR/Klassifikation) -
das entsteht in den Prompts 06/08. `matter_id` bleibt hier immer None
(Aktenzuordnung folgt in Prompt 09).
"""

from __future__ import annotations

import mimetypes
import shutil
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.ingestion.stability import compute_sha256, wait_until_stable
from app.models import AuditEvent, Document


class IntakeError(Exception):
    """Fehler bei der Erfassung einer Eingangsdatei (z. B. Datei nie stabil,
    Datei nicht lesbar). Wird bewusst als eigene Exception-Klasse gefuehrt,
    damit spaetere Aufrufer (Prompt 31, Fehler-/Retry-System) gezielt darauf
    reagieren koennen."""


class IntakeService:
    def __init__(self, storage_dir: Path | str) -> None:
        self.storage_dir = Path(storage_dir)

    def ingest_file(
        self,
        source_path: Path,
        db: Session,
        *,
        stability_timeout_seconds: float = 30.0,
    ) -> Document:
        """Erfasst eine einzelne Datei und legt einen `Document`-Datensatz an.

        Wirft `IntakeError`, wenn die Datei nicht innerhalb des Timeouts
        stabil wird oder nicht mehr existiert - in diesem Fall wird NICHTS
        kopiert und KEIN Datenbankeintrag angelegt.
        """
        source_path = Path(source_path)

        # SICHERHEITSKRITISCH (Security Review, Prompt 27): der
        # ueberwachte Scan-Ordner (app/ingestion/watcher.py) kann von
        # mehreren Personen/Geraeten (Netzlaufwerk, Scanner) beschrieben
        # werden. Ein dort abgelegter SYMLINK wuerde von
        # `shutil.copy2`/`Path.stat()` (beide folgen Symlinks per Default)
        # transparent aufgeloest - eine boesartig oder versehentlich
        # platzierte Verknuepfung auf eine Datei AUSSERHALB des Ordners
        # (z. B. eine andere Akte, eine Systemdatei) wuerde sonst
        # unbemerkt in die Kanzlei-Datenbank kopiert. Symlinks werden
        # daher grundsaetzlich abgelehnt, bevor irgendetwas gelesen wird -
        # siehe tests/test_security_review.py::test_intake_rejects_symlinks.
        if source_path.is_symlink():
            raise IntakeError(
                f"Symbolische Verknüpfungen werden aus Sicherheitsgründen "
                f"nicht erfasst: {source_path}"
            )

        if not wait_until_stable(
            source_path, timeout_seconds=stability_timeout_seconds
        ):
            raise IntakeError(
                f"Datei wurde nicht rechtzeitig stabil oder existiert nicht "
                f"mehr: {source_path}"
            )

        content_hash = compute_sha256(source_path)

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        # Eindeutiger Zieldateiname: verhindert, dass zwei gleichnamige
        # Eingangsdateien (z. B. "schreiben.pdf" von unterschiedlichen
        # Absendern) sich gegenseitig ueberschreiben.
        destination_filename = f"{uuid.uuid4()}_{source_path.name}"
        destination_path = self.storage_dir / destination_filename

        # copy2 statt move: das Original im ueberwachten Ordner bleibt
        # unangetastet - Loeschen/Verschieben von Originalen ist bewusst
        # nicht Teil dieses Service.
        shutil.copy2(source_path, destination_path)

        mime_type, _ = mimetypes.guess_type(source_path.name)

        document = Document(
            file_path=str(destination_path),
            original_filename=source_path.name,
            content_hash=content_hash,
            mime_type=mime_type,
        )
        db.add(document)
        db.flush()  # damit document.id fuer das AuditEvent verfuegbar ist

        db.add(
            AuditEvent(
                entity_type="Document",
                entity_id=document.id,
                event_type="intake_created",
                actor="system",
                details=f"Datei aus Intake erfasst: {source_path.name}",
            )
        )
        db.commit()
        db.refresh(document)
        return document
