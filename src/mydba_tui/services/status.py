"""
Global status service.

Reads MySQL global status counters for the Administration Status view.
All SQL is written to the SQL log for transparency.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from mydba_tui.logging import log_sql
from mydba_tui.services.sql_loader import tag_sql

if TYPE_CHECKING:
    from mysql.connector.abstracts import MySQLConnectionAbstract
    from mysql.connector.pooling import PooledMySQLConnection

_SQL_GLOBAL_STATUS = tag_sql("SHOW GLOBAL STATUS")


def _str(val: Any) -> str:
    """Coerce a possibly-None/bytes value to a display string."""
    if val is None:
        return ""
    if isinstance(val, (bytes, bytearray)):
        try:
            return val.decode("utf-8", "replace")
        except Exception:
            return str(val)
    return str(val)


def fetch_status(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> list[tuple[str, str]]:
    """Fetch all global status counters as sorted (name, value) pairs.

    Args:
        connection: Active MySQL connection.

    Returns:
        List of (name, value) tuples sorted by counter name.
    """
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(_SQL_GLOBAL_STATUS)
        rows = cursor.fetchall()
    finally:
        duration = time.perf_counter() - start
        log_sql(_SQL_GLOBAL_STATUS, duration, "administration.status")
        cursor.close()

    status: list[tuple[str, str]] = []
    for row in rows:
        r: Any = row
        status.append((_str(r[0]), _str(r[1])))
    status.sort(key=lambda pair: pair[0].lower())
    return status
