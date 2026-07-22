"""
Database connection package.

Provides connection management, connection profiles, and database driver
abstractions used by mydba-tui.
"""

from mydba_tui.connection.connector import ConnectionError, ConnectionResult, connect

__all__ = [
    "ConnectionError",
    "ConnectionResult",
    "connect",
]
