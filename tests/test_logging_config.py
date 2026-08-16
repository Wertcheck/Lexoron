"""Tests für app/observability/logging_config.py (Prompt 32)."""

from __future__ import annotations

import logging
import logging.handlers

import pytest

from app.observability.logging_config import (
    configure_logging,
    reset_logging_configuration_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_logging():
    reset_logging_configuration_for_tests()
    yield
    reset_logging_configuration_for_tests()


def test_configure_logging_adds_console_handler() -> None:
    configure_logging(log_level="INFO")
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) >= 1
    assert any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)


def test_configure_logging_sets_level() -> None:
    configure_logging(log_level="WARNING")
    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_is_idempotent() -> None:
    """Ein zweiter Aufruf ohne Reset darf keine doppelten Handler
    anlegen (sonst würde jede Log-Zeile mehrfach ausgegeben)."""
    configure_logging(log_level="INFO")
    handler_count_after_first = len(logging.getLogger().handlers)
    configure_logging(log_level="INFO")
    handler_count_after_second = len(logging.getLogger().handlers)
    assert handler_count_after_first == handler_count_after_second


def test_configure_logging_adds_file_handler_when_path_given(tmp_path) -> None:
    log_file = tmp_path / "logs" / "app.log"
    configure_logging(log_level="INFO", log_file_path=str(log_file))
    root_logger = logging.getLogger()
    assert any(
        isinstance(h, logging.handlers.RotatingFileHandler) for h in root_logger.handlers
    )
    assert log_file.parent.exists()


def test_configure_logging_throttles_noisy_third_party_loggers() -> None:
    configure_logging(log_level="DEBUG")
    assert logging.getLogger("watchdog").level == logging.WARNING
    assert logging.getLogger("urllib3").level == logging.WARNING


def test_invalid_log_level_setting_is_rejected() -> None:
    from app.config.settings import Settings

    with pytest.raises(Exception):  # noqa: PT011 - pydantic ValidationError
        Settings(log_level="NICHT_GUELTIG")


def test_valid_log_levels_are_normalized_to_uppercase() -> None:
    from app.config.settings import Settings

    settings = Settings(log_level="debug")
    assert settings.log_level == "DEBUG"
