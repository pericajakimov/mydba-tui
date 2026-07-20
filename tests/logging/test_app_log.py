"""Tests for the application log."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from mydba_tui.logging.app_log import setup_app_logging


@pytest.fixture(autouse=True)
def _clean_logger() -> None:
    """Remove all handlers from the mydba logger before each test."""
    logger = logging.getLogger("mydba")
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


def test_setup_creates_log_file(tmp_path: Path) -> None:
    """setup_app_logging should create the log directory and file."""
    log_file = tmp_path / "logs" / "app.log"

    with patch("mydba_tui.logging.app_log.get_app_log_path", return_value=log_file):
        logger = setup_app_logging("DEBUG")
        logger.info("test message")

    for handler in logger.handlers[:]:
        handler.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "test message" in content


def test_log_level_is_respected(tmp_path: Path) -> None:
    """Messages below the configured level should not be written."""
    log_file = tmp_path / "logs" / "app.log"

    with patch("mydba_tui.logging.app_log.get_app_log_path", return_value=log_file):
        logger = setup_app_logging("ERROR")
        logger.debug("debug msg")
        logger.info("info msg")
        logger.error("error msg")

    for handler in logger.handlers[:]:
        handler.flush()

    content = log_file.read_text(encoding="utf-8")
    assert "debug msg" not in content
    assert "info msg" not in content
    assert "error msg" in content


def test_log_format_contains_level_and_name(tmp_path: Path) -> None:
    """Log entries should contain the level and logger name."""
    log_file = tmp_path / "logs" / "app.log"

    with patch("mydba_tui.logging.app_log.get_app_log_path", return_value=log_file):
        logger = setup_app_logging("DEBUG")
        logger.warning("something happened")

    for handler in logger.handlers[:]:
        handler.flush()

    content = log_file.read_text(encoding="utf-8")
    assert "[WARNING]" in content
    assert "mydba" in content


def test_no_duplicate_handlers(tmp_path: Path) -> None:
    """Calling setup_app_logging multiple times should not add duplicate handlers."""
    log_file = tmp_path / "logs" / "app.log"

    with patch("mydba_tui.logging.app_log.get_app_log_path", return_value=log_file):
        logger = setup_app_logging("DEBUG")
        handler_count = len(logger.handlers)

        # Call again — should not add another handler
        setup_app_logging("DEBUG")
        assert len(logger.handlers) == handler_count
