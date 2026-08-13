"""E-Mail-Ingestion (Prompt 07).

Provider-Abstraktion: der Workflow/Service kennt nur `MailProvider`
(fetch_new_messages), nicht die konkrete Anbindung (IMAP, später ggf.
Microsoft Graph o. ä.). Absichtlich OHNE jede Versandfunktion - es gibt in
diesem Modul keine `send`-Methode und keinen Aufrufpfad dorthin. Das ist
keine Konfigurationsfrage, sondern eine architektonische Entscheidung:
automatischer Versand ist damit auf Code-Ebene unmöglich, nicht nur per
Einstellung deaktiviert (siehe CLAUDE.md Grundregeln).
"""

from app.mail.base import FetchedAttachment, FetchedMessage, MailProvider
from app.mail.imap_provider import ImapMailProvider
from app.mail.service import MailIngestionService

__all__ = [
    "MailProvider",
    "FetchedMessage",
    "FetchedAttachment",
    "ImapMailProvider",
    "MailIngestionService",
]
