"""
Application settings management.

Handles loading, saving, and accessing application settings stored
in settings.yaml. The settings file is created with defaults on first run.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from mydba_tui.config.defaults import (
    DEFAULT_EXPORT_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_RESULT_FORMAT,
    DEFAULT_SQL_LOG_ENABLED,
    DEFAULT_THEME,
)
from mydba_tui.config.paths import ensure_config_dir, get_settings_path


@dataclass(slots=True)
class Settings:
    """Application settings.

    Attributes:
        theme: Textual theme name (e.g. "textual-dark", "nord", "dracula").
        log_level: Application log verbosity (DEBUG, INFO, WARNING, ERROR).
        sql_log_enabled: Whether SQL statements are written to the SQL log.
        refresh_interval: Auto-refresh interval in seconds for live
            Administration tabs (one of 5, 10, 30, 60; cycled with the I key).
        export_format: Default export format (csv, tsv, sql, jsonl).
        result_format: Result table style ('mysql' for bordered, 'simple' for plain).
        format_rules: SQL formatter configuration rules.
    """

    theme: str = DEFAULT_THEME
    log_level: str = DEFAULT_LOG_LEVEL
    sql_log_enabled: bool = DEFAULT_SQL_LOG_ENABLED
    refresh_interval: int = DEFAULT_REFRESH_INTERVAL
    export_format: str = DEFAULT_EXPORT_FORMAT
    result_format: str = DEFAULT_RESULT_FORMAT
    format_rules: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.format_rules is None:
            self.format_rules = {
                "select_star_inline": True,
                "keyword_case": "upper",
                "indent_width": 2,
            }


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
        refresh_interval=data.get("refresh_interval", DEFAULT_REFRESH_INTERVAL),
        export_format=data.get("export_format", DEFAULT_EXPORT_FORMAT),
        result_format=data.get("result_format", DEFAULT_RESULT_FORMAT),
        format_rules=data.get("format_rules", None),
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

    lines = [
        "# mydba application settings",
        "# Edit this file to customize mydba behavior.",
        "#",
        "# theme: Visual theme for the application.",
        "#   Values: textual-dark, textual-light, nord, dracula, monokai,",
        "#           gruvbox, catppuccin-mocha, tokyo-night, solarized-light",
        f"theme: {settings.theme}",
        "",
        "# log_level: Application log verbosity.",
        "#   Values: DEBUG, INFO, WARNING, ERROR",
        f"log_level: {settings.log_level}",
        "",
        "# sql_log_enabled: Whether executed SQL is written to the SQL log file.",
        "#   Values: true, false",
        f"sql_log_enabled: {str(settings.sql_log_enabled).lower()}",
        "",
        "# refresh_interval: Auto-refresh interval (seconds) for live Administration tabs.",
        "#   Values: 5, 10, 30, 60 (cycle in-app with the I key)",
        f"refresh_interval: {settings.refresh_interval}",
        "",
        "# export_format: Default format for data export.",
        "#   Values: csv, tsv, sql, jsonl",
        f"export_format: {settings.export_format}",
        "",
        "# result_format: Table format for SQL Workspace query results.",
        "#   Values: mysql (bordered +---+ style), simple (plain dashes)",
        f"result_format: {settings.result_format}",
        "",
        "# format_rules: SQL formatter configuration (Ctrl+Shift+F).",
        "#   select_star_inline: Keep SELECT * on one line (true/false)",
        "#   keyword_case: Keyword casing (upper, lower, preserve)",
        "#   indent_width: Spaces per indent level (integer)",
        "format_rules:",
        f"  select_star_inline: "
        f"{str((settings.format_rules or {}).get('select_star_inline', True)).lower()}",
        f"  keyword_case: {(settings.format_rules or {}).get('keyword_case', 'upper')}",
        f"  indent_width: {(settings.format_rules or {}).get('indent_width', 2)}",
        "",
    ]

    with settings_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
