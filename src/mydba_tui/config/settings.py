"""
Application settings management.

Handles loading, saving, and accessing application settings stored
in settings.yaml. The settings file is created with defaults on first run.
"""

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from mydba_tui.config.defaults import (
    DEFAULT_EXPORT_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_PAGE_SIZE,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SQL_LOG_ENABLED,
    DEFAULT_THEME,
)
from mydba_tui.config.paths import ensure_config_dir, get_settings_path


@dataclass(slots=True)
class Settings:
    """Application settings.

    Attributes:
        theme: Name of the active visual theme.
        log_level: Application log verbosity (DEBUG, INFO, WARNING, ERROR).
        sql_log_enabled: Whether SQL statements are written to the SQL log.
        page_size: Default number of rows in result sets.
        refresh_interval: Monitoring refresh interval in seconds.
        export_format: Default export format (csv, tsv, sql, jsonl).
    """

    theme: str = DEFAULT_THEME
    log_level: str = DEFAULT_LOG_LEVEL
    sql_log_enabled: bool = DEFAULT_SQL_LOG_ENABLED
    page_size: int = DEFAULT_PAGE_SIZE
    refresh_interval: int = DEFAULT_REFRESH_INTERVAL
    export_format: str = DEFAULT_EXPORT_FORMAT


def load_settings(path: Path | None = None) -> Settings:
    """Load application settings from disk.

    If the settings file does not exist, default settings are created
    and saved automatically.

    Args:
        path: Optional override for the settings file path.

    Returns:
        Loaded application settings.
    """
    settings_path = path or get_settings_path()

    if not settings_path.exists():
        settings = Settings()
        save_settings(settings, settings_path)
        return settings

    with settings_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return Settings(
        theme=data.get("theme", DEFAULT_THEME),
        log_level=data.get("log_level", DEFAULT_LOG_LEVEL),
        sql_log_enabled=data.get("sql_log_enabled", DEFAULT_SQL_LOG_ENABLED),
        page_size=data.get("page_size", DEFAULT_PAGE_SIZE),
        refresh_interval=data.get("refresh_interval", DEFAULT_REFRESH_INTERVAL),
        export_format=data.get("export_format", DEFAULT_EXPORT_FORMAT),
    )


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Save application settings to disk.

    Creates the configuration directory if it does not exist.

    Args:
        settings: Settings instance to save.
        path: Optional override for the settings file path.
    """
    settings_path = path or get_settings_path()
    ensure_config_dir()

    data = asdict(settings)

    with settings_path.open("w", encoding="utf-8") as f:
        f.write("# mydba application settings\n")
        f.write("# See docs/13-configuration.md for details.\n\n")
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
