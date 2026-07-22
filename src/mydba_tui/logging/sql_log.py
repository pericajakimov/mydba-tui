"""
SQL log.

Records every SQL statement executed against the database server.
Each entry contains a timestamp, execution duration, source module,
and the SQL text collapsed to a single line.

The SQL log is intentionally separate from the application log.
It exists for transparency, debugging, and query optimization.
"""

import re
from datetime import datetime
from pathlib import Path

from mydba_tui.config.paths import get_config_dir

SQL_LOG_FILENAME = "sql.log"
"""Default SQL log filename."""

_WHITESPACE_PATTERN = re.compile(r"\s+")
"""Pattern matching consecutive whitespace characters."""

_LINE_COMMENT_PATTERN = re.compile(r"--[^\n]*|#[^\n]*")
"""Pattern matching SQL single-line comments (-- or # to end of line)."""

_BLOCK_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)
"""Pattern matching SQL block comments (/* ... */)."""


def get_sql_log_path() -> Path:
    """Return the path to the SQL log file.

    Returns:
        Path to sql.log inside the logs directory.
    """
    return get_config_dir() / "logs" / SQL_LOG_FILENAME


def collapse_sql(sql: str) -> str:
    """Collapse a multi-line SQL statement into a single line.

    Removes SQL comments (--, #, and /* */ styles), replaces all newlines,
    tabs, and consecutive spaces with a single space. This ensures every
    SQL log entry occupies exactly one line, making the log grep-friendly.

    Args:
        sql: Raw SQL text, possibly multi-line with comments.

    Returns:
        Single-line SQL string without comments.
    """
    # Remove block comments first (can span multiple lines)
    cleaned = _BLOCK_COMMENT_PATTERN.sub("", sql)
    # Remove single-line comments
    cleaned = _LINE_COMMENT_PATTERN.sub("", cleaned)
    return _WHITESPACE_PATTERN.sub(" ", cleaned).strip()


def log_sql(sql: str, duration_seconds: float, source: str) -> None:
    """Write a SQL statement to the SQL log.

    Each log entry has the format:
        2024-01-15 10:23:45 | 0.023s | browser.tables | SELECT ...

    Args:
        sql: The SQL statement that was executed.
        duration_seconds: Execution time in seconds.
        source: Identifier for the originating module (e.g. "browser.tables",
            "server.detection", "workspace.execute").
    """
    log_path = get_sql_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration = f"{duration_seconds:.3f}s"
    collapsed = collapse_sql(sql)

    line = f"{timestamp} | {duration} | {source} | {collapsed}\n"

    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)
