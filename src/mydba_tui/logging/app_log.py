"""
Application log setup.

Configures Python's standard logging for internal application events,
errors, and debug information. The application log never contains SQL
statements — those belong exclusively in the SQL log.
"""

import logging
from pathlib import Path

from mydba_tui.config.paths import get_config_dir

APP_LOG_FILENAME = "app.log"
"""Default application log filename."""

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
"""Log line format."""

LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
"""Timestamp format for log entries."""


def get_app_log_path() -> Path:
    """Return the path to the application log file.

    Returns:
        Path to app.log inside the logs directory.
    """
    return get_config_dir() / "logs" / APP_LOG_FILENAME


def setup_app_logging(level: str = "WARNING") -> logging.Logger:
    """Configure application logging.

    Sets up a file handler that writes to ~/.config/mydba/logs/app.log.
    Creates the logs directory if it does not exist.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).

    Returns:
        The root application logger.
    """
    log_path = get_app_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("mydba")
    logger.setLevel(getattr(logging, level.upper(), logging.WARNING))

    # Avoid adding duplicate handlers on repeated calls.
    if not logger.handlers:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        logger.addHandler(handler)

    return logger
