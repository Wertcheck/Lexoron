"""MailIngestionService – überführt abgerufene Nachrichten ins Datenmodell.

Ablauf (Konzept Prompt 07): Absender, Empfänger, Betreff, Datum,
Message-ID, Body und Anhänge erfassen; Anhänge werden EINZELN als
`Document` verarbeitet (wie Dateien aus dem Scan-Intake, Prompt 05) -
NICHT als Teil des Message-Textes.

Enthält bewusst KEINE automatische Antwort und KEINEN automatischen
Versand - der `MailProvider`, von dem dieser Service abhängt, hat
strukturell keine Sende-Methode (siehe app/mail/base.py).
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.mail.base import FetchedAttachment, FetchedMessage, MailProvider
from app.models import AuditEvent, Document, Message


class MailIngestionService:
    def __init__(self, provider: MailProvider, attachment_storage_dir: Path | str) -> None:
        self.provider = provider
        self.attachment_storage_dir = Path(attachment_storage_dir)

    def ingest_new_messages(self, db: Session) -> list[Message]:
        """Ruft neue Nachrichten über den Provider ab und legt für jede
        noch nicht bekannte Nachricht einen `Message`-Datensatz samt
        `Document`-Einträgen für Anhänge an.

        Nachrichten mit einer bereits bekannten `external_message_id`
        werden übersprungen (Deduplizierung) - wichtig, falls ein
        Provider trotz `mark_seen` dieselbe Nachricht erneut liefert.
        """
        fetched_messages = self.provider.fetch_new_messages()
        created_messages: list[Message] = []

        for fetched in fetched_messages:
            if self._already_ingested(fetched, db):
                continue
            message = self._create_message(fetched, db)
            created_messages.append(message)

        return created_messages

    def _already_ingested(self, fetched: FetchedMessage, db: Session) -> bool:
        if not fetched.external_message_id:
            return False
        existing = (
            db.query(Message)
            .filter_by(external_message_id=fetched.external_message_id)
            .first()
        )
        return existing is not None

    def _create_message(self, fetched: FetchedMessage, db: Session) -> Message:
        message = Message(
            external_message_id=fetched.external_message_id,
            direction="inbound",
            sender=fetched.sender,
            recipient=fetched.recipient,
            subject=fetched.subject,
            body_text=fetched.body_text,
        )
        db.add(message)
        db.flush()  # message.id fuer Anhaenge und Audit-Event verfuegbar

        for attachment in fetched.attachments:
            self._store_attachment(attachment, message, db)

        db.add(
            AuditEvent(
                entity_type="Message",
                entity_id=message.id,
                event_type="mail_ingested",
                actor="system",
                details=(
                    f"E-Mail erfasst, Absender: {fetched.sender or 'unbekannt'}, "
                    f"{len(fetched.attachments)} Anhang/Anhänge"
                ),
            )
        )
        db.commit()
        db.refresh(message)
        return message

    def _store_attachment(
        self, attachment: FetchedAttachment, message: Message, db: Session
    ) -> Document:
        self.attachment_storage_dir.mkdir(parents=True, exist_ok=True)
        destination_filename = f"{uuid.uuid4()}_{attachment.filename}"
        destination_path = self.attachment_storage_dir / destination_filename
        destination_path.write_bytes(attachment.content)

        content_hash = hashlib.sha256(attachment.content).hexdigest()

        document = Document(
            message_id=message.id,
            file_path=str(destination_path),
            original_filename=attachment.filename,
            mime_type=attachment.mime_type,
            content_hash=content_hash,
        )
        db.add(document)
        return document
