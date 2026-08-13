"""IMAP-Adapter (konkrete `MailProvider`-Implementierung).

Nutzt ausschliesslich `imaplib` aus der Python-Standardbibliothek - keine
zusaetzliche Abhaengigkeit noetig. Ruft nur ungelesene Nachrichten ab und
markiert sie optional als gelesen (`mail_mark_seen`), sendet aber NIEMALS
etwas - `imaplib` wird hier ausschliesslich lesend verwendet (kein SMTP,
kein Aufruf einer Sende-Funktion).
"""

from __future__ import annotations

import imaplib

from app.mail.base import FetchedMessage, MailProvider
from app.mail.parsing import parse_raw_email


class ImapMailProvider(MailProvider):
    def __init__(
        self,
        *,
        host: str,
        port: int = 993,
        username: str,
        password: str,
        mailbox: str = "INBOX",
        use_ssl: bool = True,
        mark_seen: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.mailbox = mailbox
        self.use_ssl = use_ssl
        self.mark_seen = mark_seen

    def _connect(self) -> imaplib.IMAP4:
        connection: imaplib.IMAP4
        if self.use_ssl:
            connection = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            connection = imaplib.IMAP4(self.host, self.port)
        connection.login(self.username, self.password)
        connection.select(self.mailbox)
        return connection

    def fetch_new_messages(self) -> list[FetchedMessage]:
        connection = self._connect()
        try:
            # UNSEEN statt ALL: verhindert, dass bei jedem Lauf der
            # komplette Postfachinhalt erneut abgerufen wird. Zusaetzlicher
            # Schutz gegen Duplikate erfolgt ueber die externe Message-ID
            # im MailIngestionService.
            status, message_numbers = connection.search(None, "UNSEEN")
            if status != "OK":
                return []

            fetched_messages: list[FetchedMessage] = []
            for message_number in message_numbers[0].split():
                fetch_status, message_data = connection.fetch(
                    message_number, "(RFC822)"
                )
                if fetch_status != "OK" or not message_data or not message_data[0]:
                    continue
                raw_bytes = message_data[0][1]
                fetched_messages.append(parse_raw_email(raw_bytes))

                if self.mark_seen:
                    connection.store(message_number, "+FLAGS", "\\Seen")

            return fetched_messages
        finally:
            try:
                connection.close()
            except imaplib.IMAP4.error:
                pass
            connection.logout()
