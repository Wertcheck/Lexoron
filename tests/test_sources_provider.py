"""Tests fuer app/sources/provider.py (Prompt 14)."""

from app.sources.provider import ManualSourceProvider
from app.sources.schema import SourceImport


def test_manual_provider_returns_data_unchanged() -> None:
    data = SourceImport(title="§ 370 AO", source_type="Gesetz", reference="AO § 370")
    provider = ManualSourceProvider()

    result = provider.resolve(data)

    assert result == data


def test_manual_provider_has_expected_name() -> None:
    assert ManualSourceProvider.name == "manual"


def test_manual_provider_never_invents_fields() -> None:
    """Kernanforderung: der Provider fuegt KEINE Werte hinzu, die der
    Anwalt nicht selbst angegeben hat."""
    data = SourceImport(title="Titel", source_type="Sonstiges")
    provider = ManualSourceProvider()

    result = provider.resolve(data)

    assert result.reference is None
    assert result.url is None
    assert result.document_date is None
