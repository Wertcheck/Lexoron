"""Tests fuer app/ai_providers/claude_writing_provider.py.

Es gibt bewusst noch keine konkrete Implementierung - dieser Test prueft
nur, dass das Protocol die erwartete, minimale Form hat (analog zum
Test fuer MailProvider in test_mail_service.py)."""

from app.ai_providers.claude_writing_provider import ClaudeWritingProvider


def test_protocol_has_exactly_one_method() -> None:
    public_methods = [
        name for name in dir(ClaudeWritingProvider) if not name.startswith("_")
    ]
    assert public_methods == ["write"]


def test_fake_implementation_satisfies_protocol() -> None:
    from app.privacy.gateway_schema import ClaudeRequestPayload

    class FakeProvider:
        def write(self, payload: ClaudeRequestPayload) -> str:
            return "Antwort"

    provider: ClaudeWritingProvider = FakeProvider()
    payload = ClaudeRequestPayload(
        schreibauftrag="formulate_draft", anonymisierter_sachverhalt="Text"
    )
    assert provider.write(payload) == "Antwort"
