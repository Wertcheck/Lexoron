"""Tests für app/setup/paths.py (Prompt 36/37)."""

import os
from pathlib import Path

from app.setup.paths import resolve_data_dir


def test_override_env_var_takes_precedence(monkeypatch, tmp_path) -> None:
    custom = tmp_path / "custom-data-dir"
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(custom))
    assert resolve_data_dir() == custom


def test_windows_default_uses_programdata(monkeypatch) -> None:
    monkeypatch.delenv("KANZLEI_AI_DATA_DIR", raising=False)
    monkeypatch.setenv("PROGRAMDATA", r"C:\ProgramData")
    assert resolve_data_dir(is_windows=True) == Path(r"C:\ProgramData") / "KanzleiAI"


def test_windows_default_falls_back_without_programdata_env(monkeypatch) -> None:
    monkeypatch.delenv("KANZLEI_AI_DATA_DIR", raising=False)
    monkeypatch.delenv("PROGRAMDATA", raising=False)
    assert resolve_data_dir(is_windows=True) == Path(r"C:\ProgramData") / "KanzleiAI"


def test_non_windows_fallback_is_home_based(monkeypatch) -> None:
    monkeypatch.delenv("KANZLEI_AI_DATA_DIR", raising=False)
    assert resolve_data_dir(is_windows=False) == Path.home() / ".kanzlei_ai"


def test_auto_detection_matches_actual_platform(monkeypatch) -> None:
    """Ohne explizite Angabe muss `resolve_data_dir()` genau dem Zweig
    entsprechen, den `os.name` auf der tatsächlichen Plattform auswählen
    würde (das Projekt läuft nur auf Windows, siehe CLAUDE.md - hier nur
    als Konsistenzbeweis zwischen Auto-Erkennung und explizitem Aufruf)."""
    monkeypatch.delenv("KANZLEI_AI_DATA_DIR", raising=False)
    expected = resolve_data_dir(is_windows=(os.name == "nt"))
    assert resolve_data_dir() == expected
