"""
Logging package.

Provides two independent logging systems:

1. Application log — internal events, errors, debug info (Python logging).
2. SQL log — every SQL statement executed against the server.

These two systems are intentionally separate. The application log never
contains SQL statements, and the SQL log never contains Python debug messages.
"""

from mydba_tui.logging.app_log import get_app_log_path, setup_app_logging
from mydba_tui.logging.sql_log import collapse_sql, get_sql_log_path, log_sql

__all__ = [
    "collapse_sql",
    "get_app_log_path",
    "get_sql_log_path",
    "log_sql",
    "setup_app_logging",
]
