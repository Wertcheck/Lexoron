"""Tests für app/local_ai/model_catalog.py (§67)."""

from __future__ import annotations

from app.local_ai.model_catalog import get_model_catalog


def test_catalog_is_not_empty() -> None:
    assert len(get_model_catalog()) > 0


def test_all_entries_use_ollama_runtime() -> None:
    assert all(entry.runtime == "ollama" for entry in get_model_catalog())


def test_all_entries_have_unique_tags() -> None:
    tags = [entry.tag for entry in get_model_catalog()]
    assert len(tags) == len(set(tags))


def test_all_entries_have_unique_recommendation_priority() -> None:
    priorities = [entry.recommendation_priority for entry in get_model_catalog()]
    assert len(priorities) == len(set(priorities))


def test_larger_download_size_never_has_lower_min_ram() -> None:
    """Monotonie-Pruefung: ein groesseres Modell darf nie eine NIEDRIGERE
    RAM-Anforderung haben als ein kleineres - waere ein Widerspruch in
    den Katalogdaten."""
    entries = sorted(get_model_catalog(), key=lambda e: e.download_size_gb)
    for previous, current in zip(entries, entries[1:]):
        assert current.min_ram_gb >= previous.min_ram_gb


def test_recommended_values_are_never_below_minimum() -> None:
    for entry in get_model_catalog():
        assert entry.recommended_ram_gb >= entry.min_ram_gb
        assert entry.recommended_vram_gb >= entry.min_vram_gb


def test_no_fabricated_negative_or_zero_sizes() -> None:
    for entry in get_model_catalog():
        assert entry.download_size_gb > 0
        assert entry.min_ram_gb > 0
        assert entry.context_length > 0


def test_capabilities_and_limitations_are_never_empty() -> None:
    """Vorgabe: Lexoron muss verstaendlich erklaeren koennen, wofuer ein
    Modell geeignet ist und wofuer nicht."""
    for entry in get_model_catalog():
        assert len(entry.capability_profile) > 0
        assert len(entry.limitations) > 0


def test_no_model_claims_to_replace_claude_or_provide_legal_advice() -> None:
    """Vorgabe, woertlich: keine Behauptung, ein lokales Modell liefere
    eigenstaendig Rechtsberatung oder ersetze Claude."""
    for entry in get_model_catalog():
        limitations_text = " ".join(entry.limitations).lower()
        assert "claude" in limitations_text or "rechtsberatung" in limitations_text
