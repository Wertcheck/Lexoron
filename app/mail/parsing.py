"""Parsing von rohen E-Mail-Bytes (RFC 822) zu `FetchedMessage`.

Bewusst getrennt von der IMAP-Verbindung selbst (app/mail/imap_provider.py),
damit das Parsing ohne echten Mailserver getestet werden kann. Extrahiert
nur Metadaten und Inhalte - keine inhaltliche/juristische Interpretation
(die kommt erst mit der Klassifikation in Prompt 08).
"""

from __future__ import annotations

from datetime import datetime
from email import message_from_bytes, utils as email_utils
from email.message import Message as EmailMessage

from app.mail.base import FetchedAttachment, FetchedMessage


def _decode_header_value(value: str | None) -> str | None:
    if value is None:
        return None
    # E-Mail-Header koennen kodierte Wortfolgen enthalten (RFC 2047),
    # z. B. "=?UTF-8?B?...?=" bei nicht-ASCII-Betreffzeilen.
    from email.header import decode_header

    parts = decode_header(value)
    decoded_parts: list[str] = []
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded_parts.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            decoded_parts.append(text)
    return "".join(decoded_parts)


def _extract_body_text(email_message: EmailMessage) -> str | None:
    """Bevorzugt text/plain; faellt auf eine grobe Bereinigung von
    text/html zurueck, falls kein Klartext-Teil vorhanden ist."""
    if email_message.is_multipart():
        plain_part = None
        html_part = None
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = part.get_content_disposition()
            if content_disposition == "attachment":
                continue
            if content_type == "text/plain" and plain_part is None:
                plain_part = part
            elif content_type == "text/html" and html_part is None:
                html_part = part
        chosen = plain_part or html_part
        if chosen is None:
            return None
        payload = chosen.get_payload(decode=True)
        if payload is None:
            return None
        charset = chosen.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    payload = email_message.get_payload(decode=True)
    if payload is None:
        return None
    charset = email_message.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _extract_attachments(email_message: EmailMessage) -> list[FetchedAttachment]:
    attachments: list[FetchedAttachment] = []
    if not email_message.is_multipart():
        return attachments

    for part in email_message.walk():
        if part.get_content_disposition() != "attachment":
            continue
        filename = part.get_filename()
        if not filename:
            continue
        filename = _decode_header_value(filename) or filename
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        attachments.append(
            FetchedAttachment(
                filename=filename,
                content=payload,
                mime_type=part.get_content_type(),
            )
        )
    return attachments


def _parse_received_at(email_message: EmailMessage) -> datetime | None:
    date_header = email_message.get("Date")
    if not date_header:
        return None
    parsed = email_utils.parsedate_to_datetime(date_header)
    return parsed


def parse_raw_email(raw: bytes) -> FetchedMessage:
    """Parst rohe RFC-822-Bytes einer E-Mail zu `FetchedMessage`."""
    email_message = message_from_bytes(raw)

    return FetchedMessage(
        external_message_id=email_message.get("Message-ID"),
        sender=_decode_header_value(email_message.get("From")),
        recipient=_decode_header_value(email_message.get("To")),
        subject=_decode_header_value(email_message.get("Subject")),
        body_text=_extract_body_text(email_message),
        received_at=_parse_received_at(email_message),
        attachments=_extract_attachments(email_message),
    )
