"""
Global variables service.

Reads MySQL global variables for the Administration Variables view.
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

_SQL_GLOBAL_VARIABLES = tag_sql("SHOW GLOBAL VARIABLES")


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


def fetch_variables(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> list[tuple[str, str]]:
    """Fetch all global variables as sorted (name, value) pairs.

    Args:
        connection: Active MySQL connection.

    Returns:
        List of (name, value) tuples sorted by variable name.
    """
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(_SQL_GLOBAL_VARIABLES)
        rows = cursor.fetchall()
    finally:
        duration = time.perf_counter() - start
        log_sql(_SQL_GLOBAL_VARIABLES, duration, "administration.variables")
        cursor.close()

    variables: list[tuple[str, str]] = []
    for row in rows:
        r: Any = row
        variables.append((_str(r[0]), _str(r[1])))
    variables.sort(key=lambda pair: pair[0].lower())
    return variables
