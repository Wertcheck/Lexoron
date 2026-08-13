"""Provider-Abstraktion für E-Mail-Ingestion.

`MailProvider` ist bewusst ein `Protocol` mit genau EINER Methode
(`fetch_new_messages`) - es gibt strukturell keine Möglichkeit, über diese
Abstraktion eine E-Mail zu senden. Der Workflow (MailIngestionService)
hängt nur von diesem Protocol ab, nie von einer konkreten
Provider-Implementierung (siehe Konzept Prompt 07: "Provider-Abstraktion,
... aber entkopple ihn vom Workflow").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class FetchedAttachment:
    filename: str
    content: bytes
    mime_type: str | None = None


@dataclass
class FetchedMessage:
    external_message_id: str | None
    sender: str | None
    recipient: str | None
    subject: str | None
    body_text: str | None
    received_at: datetime | None
    attachments: list[FetchedAttachment] = field(default_factory=list)


class MailProvider(Protocol):
    def fetch_new_messages(self) -> list[FetchedMessage]:
        """Ruft neue Nachrichten ab. Enthält absichtlich keine Methode zum
        Senden - Versand ist über diese Abstraktion nicht möglich."""
        ...
