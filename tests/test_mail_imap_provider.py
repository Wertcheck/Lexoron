"""Tests fuer app/mail/imap_provider.py (Prompt 07).

Mockt `imaplib.IMAP4_SSL`, da kein echter IMAP-Server verfuegbar ist (und
fuer synthetische Tests auch nicht sein soll). Prueft den Ablauf: login,
select, UNSEEN-Suche, Abruf per Nachricht, Parsing, optionales Markieren
als gelesen - und dass ausschliesslich lesend auf das Postfach zugegriffen
wird (kein SMTP/Sendeaufruf existiert in dieser Klasse ueberhaupt)."""

from email.message import EmailMessage
from unittest.mock import MagicMock, patch

from app.mail.imap_provider import ImapMailProvider


def _make_raw_email(message_id: str) -> bytes:
    msg = EmailMessage()
    msg["From"] = "mandant@example.test"
    msg["Subject"] = "Testnachricht"
    msg["Message-ID"] = message_id
    msg.set_content("Testinhalt")
    return bytes(msg)


@patch("app.mail.imap_provider.imaplib.IMAP4_SSL")
def test_fetch_new_messages_returns_parsed_messages(mock_imap_ssl_cls) -> None:
    mock_connection = MagicMock()
    mock_imap_ssl_cls.return_value = mock_connection
    mock_connection.search.return_value = ("OK", [b"1 2"])
    mock_connection.fetch.side_effect = [
        ("OK", [(b"1 (RFC822 {123}", _make_raw_email("<eins@example.test>"))]),
        ("OK", [(b"2 (RFC822 {123}", _make_raw_email("<zwei@example.test>"))]),
    ]

    provider = ImapMailProvider(
        host="imap.example.test",
        username="kanzlei@example.test",
        password="testpasswort",
    )
    result = provider.fetch_new_messages()

    assert len(result) == 2
    assert {m.external_message_id for m in result} == {
        "<eins@example.test>",
        "<zwei@example.test>",
    }
    mock_connection.login.assert_called_once_with(
        "kanzlei@example.test", "testpasswort"
    )
    mock_connection.select.assert_called_once_with("INBOX")
    mock_connection.search.assert_called_once_with(None, "UNSEEN")


@patch("app.mail.imap_provider.imaplib.IMAP4_SSL")
def test_fetch_marks_messages_as_seen_when_configured(mock_imap_ssl_cls) -> None:
    mock_connection = MagicMock()
    mock_imap_ssl_cls.return_value = mock_connection
    mock_connection.search.return_value = ("OK", [b"1"])
    mock_connection.fetch.return_value = (
        "OK",
        [(b"1 (RFC822 {1}", _make_raw_email("<x@example.test>"))],
    )

    provider = ImapMailProvider(
        host="imap.example.test",
        username="kanzlei@example.test",
        password="testpasswort",
        mark_seen=True,
    )
    provider.fetch_new_messages()

    mock_connection.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")


@patch("app.mail.imap_provider.imaplib.IMAP4_SSL")
def test_fetch_does_not_mark_seen_when_disabled(mock_imap_ssl_cls) -> None:
    mock_connection = MagicMock()
    mock_imap_ssl_cls.return_value = mock_connection
    mock_connection.search.return_value = ("OK", [b"1"])
    mock_connection.fetch.return_value = (
        "OK",
        [(b"1 (RFC822 {1}", _make_raw_email("<x@example.test>"))],
    )

    provider = ImapMailProvider(
        host="imap.example.test",
        username="kanzlei@example.test",
        password="testpasswort",
        mark_seen=False,
    )
    provider.fetch_new_messages()

    mock_connection.store.assert_not_called()


@patch("app.mail.imap_provider.imaplib.IMAP4_SSL")
def test_fetch_closes_and_logs_out_connection(mock_imap_ssl_cls) -> None:
    mock_connection = MagicMock()
    mock_imap_ssl_cls.return_value = mock_connection
    mock_connection.search.return_value = ("OK", [b""])

    provider = ImapMailProvider(
        host="imap.example.test", username="u", password="p"
    )
    provider.fetch_new_messages()

    mock_connection.close.assert_called_once()
    mock_connection.logout.assert_called_once()


def test_imap_provider_has_no_send_method() -> None:
    """Architektonischer Schutz: keine Methode, die auch nur entfernt nach
    Versand klingt, existiert auf dieser Klasse."""
    public_methods = {
        name for name in dir(ImapMailProvider) if not name.startswith("_")
    }
    forbidden_terms = {"send", "smtp", "reply", "forward"}
    for method_name in public_methods:
        assert not any(term in method_name.lower() for term in forbidden_terms)
