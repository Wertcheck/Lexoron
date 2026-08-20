"""Tests für app/logs/service.py (Schritt 3, Teil 2)."""

from __future__ import annotations

from pathlib import Path

from app.logs.service import LogAccessService


def test_no_log_file_configured_returns_empty(tmp_path: Path) -> None:
    service = LogAccessService()
    assert service.read_tail(None) == []
    assert service.anonymized_download_content(None) is None


def test_missing_log_file_returns_empty(tmp_path: Path) -> None:
    service = LogAccessService()
    missing = tmp_path / "does_not_exist.log"
    assert service.read_tail(str(missing)) == []
    assert service.anonymized_download_content(str(missing)) is None


def test_read_tail_returns_last_n_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("\n".join(f"Zeile {i}" for i in range(10)), encoding="utf-8")

    result = LogAccessService().read_tail(str(log_path), max_lines=3)

    assert result == ["Zeile 7", "Zeile 8", "Zeile 9"]


def test_pii_is_redacted_before_returning(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "INFO app.mail Fehler beim Abruf fuer max.mustermann@kanzlei-mandant.de",
        encoding="utf-8",
    )

    result = LogAccessService().read_tail(str(log_path))

    assert "max.mustermann@kanzlei-mandant.de" not in "\n".join(result)


def test_download_content_is_anonymized(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "ERROR IBAN erkannt: DE89370400440532013000", encoding="utf-8"
    )

    content = LogAccessService().anonymized_download_content(str(log_path))

    assert content is not None
    assert "DE89370400440532013000" not in content
