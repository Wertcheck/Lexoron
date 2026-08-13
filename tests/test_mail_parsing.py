"""Tests fuer app/mail/parsing.py (Prompt 07).

Nutzt ausschliesslich synthetisch mit Pythons email-Paket erzeugte
Test-Nachrichten - kein echter Mailserver, keine echten Mandantendaten.
"""

from email.message import EmailMessage
from email.utils import formatdate

from app.mail.parsing import parse_raw_email


def test_parses_simple_plain_text_message() -> None:
    msg = EmailMessage()
    msg["From"] = "mandant@example.test"
    msg["To"] = "kanzlei@example.test"
    msg["Subject"] = "Frage zu meinem Fall"
    msg["Message-ID"] = "<abc123@example.test>"
    msg["Date"] = formatdate()
    msg.set_content("Sehr geehrte Damen und Herren, dies ist ein Testinhalt.")

    result = parse_raw_email(bytes(msg))

    assert result.sender == "mandant@example.test"
    assert result.recipient == "kanzlei@example.test"
    assert result.subject == "Frage zu meinem Fall"
    assert result.external_message_id == "<abc123@example.test>"
    assert result.body_text is not None
    assert "Testinhalt" in result.body_text
    assert result.received_at is not None
    assert result.attachments == []


def test_parses_message_with_umlauts_in_subject() -> None:
    """Betreffzeilen mit Umlauten werden oft kodiert uebertragen
    (RFC 2047) - muss korrekt dekodiert werden."""
    msg = EmailMessage()
    msg["From"] = "mandant@example.test"
    msg["To"] = "kanzlei@example.test"
    msg["Subject"] = "Rückfrage zur Kündigungsfrist"
    msg["Message-ID"] = "<umlaut@example.test>"
    msg.set_content("Testinhalt mit Ümlauten.")

    result = parse_raw_email(bytes(msg))

    assert result.subject == "Rückfrage zur Kündigungsfrist"


def test_parses_message_with_attachment() -> None:
    msg = EmailMessage()
    msg["From"] = "mandant@example.test"
    msg["To"] = "kanzlei@example.test"
    msg["Subject"] = "Anbei das Schreiben"
    msg["Message-ID"] = "<mit-anhang@example.test>"
    msg.set_content("Siehe Anhang.")
    msg.add_attachment(
        b"Synthetischer PDF-Inhalt",
        maintype="application",
        subtype="pdf",
        filename="schreiben.pdf",
    )

    result = parse_raw_email(bytes(msg))

    assert result.body_text is not None
    assert "Siehe Anhang" in result.body_text
    assert len(result.attachments) == 1
    assert result.attachments[0].filename == "schreiben.pdf"
    assert result.attachments[0].content == b"Synthetischer PDF-Inhalt"
    assert result.attachments[0].mime_type == "application/pdf"


def test_parses_message_with_multiple_attachments() -> None:
    msg = EmailMessage()
    msg["From"] = "mandant@example.test"
    msg["Message-ID"] = "<mehrere-anhaenge@example.test>"
    msg.set_content("Zwei Anhänge im Test.")
    msg.add_attachment(
        b"Inhalt A", maintype="application", subtype="pdf", filename="a.pdf"
    )
    msg.add_attachment(
        b"Inhalt B", maintype="application", subtype="pdf", filename="b.pdf"
    )

    result = parse_raw_email(bytes(msg))

    assert len(result.attachments) == 2
    filenames = {a.filename for a in result.attachments}
    assert filenames == {"a.pdf", "b.pdf"}


def test_message_without_message_id_still_parses() -> None:
    msg = EmailMessage()
    msg["From"] = "mandant@example.test"
    msg.set_content("Kein Message-ID-Header gesetzt.")

    result = parse_raw_email(bytes(msg))

    assert result.external_message_id is None
    assert result.body_text is not None
