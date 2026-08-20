"""ClientExportService – DSGVO-Datenauszug fuer EINEN Mandanten (20.08.).

Wiederverwendet bewusst `MatterExportService.build_manifest`
(app/export/service.py, urspruenglich Prompt 35 fuer den Aktenexport) statt
einer zweiten, abweichenden Implementierung: pro Akte des Mandanten wird
exakt dasselbe, bereits fuer DSGVO Art. 15/20 konzipierte Manifest-Format
gebaut (Nachrichten, Dokumente-Metadaten+Volltext, Entwuerfe, Fristen,
Anmerkungen, Postausgang-Status, Audit-Trail) und zusammen mit den
Original-Dokumentdateien in EIN gemeinsames ZIP gepackt - "Datenauszug fuer
den Mandanten" bedeutet hier "alle seine Akten", nicht nur die
Client-Stammdaten selbst.

Wie MatterExportService: enthaelt UNPSEUDONYMISIERTE Mandanteninhalte
(das ist der Zweck eines Auskunftsersuchens) - genauso schuetzenswert wie
die Produktionsdatenbank.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.export.service import MatterExportService, json_default
from app.models import Client, Document


class ClientNotFoundError(Exception):
    pass


class ClientExportService:
    def __init__(self) -> None:
        self._matter_export = MatterExportService()

    def export_client(self, client_id: str, db: Session, output_dir: str | Path) -> Path:
        client = db.get(Client, client_id)
        if client is None:
            raise ClientNotFoundError(f"Mandant {client_id} nicht gefunden")

        manifest = self._build_client_manifest(client, db)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_number = (client.client_number or client.id).replace("/", "-")
        archive_path = output_dir / f"mandant_datenauszug_{safe_number}_{timestamp}.zip"

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2, default=json_default),
            )
            for matter in client.matters:
                documents = db.query(Document).filter_by(matter_id=matter.id).all()
                for document in documents:
                    source_path = Path(document.file_path)
                    if source_path.exists():
                        arcname = (
                            f"akten/{matter.id}/documents/{document.id}_{source_path.name}"
                        )
                        archive.write(source_path, arcname=arcname)
            archive.writestr(
                "AUSZUG_INFO.txt",
                (
                    f"Lexono Mandanten-Datenauszug - Mandant: {client.name}\n"
                    f"Erstellt: {timestamp}\n"
                    "Enthaelt saemtliche mit diesem Mandanten verknuepften Akten "
                    "(Nachrichten, Dokumente, Entwuerfe, Fristen, Audit-Trail) - "
                    "unpseudonymisiert, wie die Produktionsdatenbank selbst zu "
                    "behandeln. Diese Datei ist ein technischer Datenauszug, KEINE "
                    "rechtliche Bewertung einer Auskunftspflicht.\n"
                ),
            )

        return archive_path

    def _build_client_manifest(self, client: Client, db: Session) -> dict[str, Any]:
        return {
            "client": {
                "id": client.id,
                "name": client.name,
                "client_number": client.client_number,
                "contact_email": client.contact_email,
                "contact_phone": client.contact_phone,
                "practice_area": client.practice_area,
                "status": client.status,
                "responsible_user_email": (
                    client.responsible_user.email if client.responsible_user else None
                ),
                "created_at": client.created_at,
            },
            "matters": [
                self._matter_export.build_manifest(matter, db) for matter in client.matters
            ],
        }
