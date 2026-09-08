"""
Metadata lock waits service.

Reads table metadata-lock (MDL) blocking information for the Administration
Metadata Locks view — sessions blocked waiting on a table's metadata lock and
the session holding it (the classic "Waiting for table metadata lock" case,
e.g. an ALTER blocked by an open transaction). Sourced from the sys schema
(sys.schema_table_lock_waits). All SQL is written to the SQL log.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mydba_tui.logging import log_sql
from mydba_tui.services.sql_loader import load_sql

if TYPE_CHECKING:
    from mysql.connector.abstracts import MySQLConnectionAbstract
    from mysql.connector.pooling import PooledMySQLConnection

# Columns presented, in display order.
MDL_COLUMNS = [
    "Wait Age",
    "Object",
    "Waiting PID",
    "Waiting Account",
    "Waiting Lock",
    "Waiting Query",
    "Blocking PID",
    "Blocking Account",
    "Blocking Lock",
]

_SQL_FILE_MDL_WAITS = "admin/metadata_lock_waits.sql"


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


def _int(val: Any) -> int:
    """Coerce a possibly-None numeric value to int (0 on failure)."""
    if val is None:
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


@dataclass(slots=True)
class MetadataLockWait:
    """A single metadata-lock wait (a blocked/blocking pair on a table).

    Attributes:
        wait_age_secs: Seconds the waiting statement has been blocked.
        object_schema: Schema of the locked object.
        object_name: Name of the locked object.
        waiting_pid: Processlist id of the blocked session.
        waiting_account: Account (user@host) of the blocked session.
        waiting_lock_type: MDL type the blocked session requested.
        waiting_query: Statement the blocked session is waiting on.
        blocking_pid: Processlist id of the blocking session.
        blocking_account: Account (user@host) of the blocking session.
        blocking_lock_type: MDL type held by the blocking session.
    """

    wait_age_secs: int
    object_schema: str
    object_name: str
    waiting_pid: int
    waiting_account: str
    waiting_lock_type: str
    waiting_query: str
    blocking_pid: int
    blocking_account: str
    blocking_lock_type: str


def fetch_metadata_lock_waits(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> list[MetadataLockWait]:
    """Fetch table metadata-lock waits, longest-waiting first.

    Best-effort: returns an empty list if the sys schema view is unavailable
    (e.g. on MariaDB or when the sys schema is not installed).

    Args:
        connection: Active MySQL connection.

    Returns:
        List of MetadataLockWait sorted by wait age descending, or [] if
        unavailable.
    """
    sql = load_sql(_SQL_FILE_MDL_WAITS)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(sql)
        description = cursor.description or []
        col_names = [desc[0] for desc in description]
        raw_rows = cursor.fetchall()
    except Exception:
        col_names = []
        raw_rows = []
    finally:
        duration = time.perf_counter() - start
        log_sql(sql, duration, "administration.metadata_locks")
        cursor.close()

    idx = {name.lower(): i for i, name in enumerate(col_names)}

    def _get(row: Any, key: str, pos: int) -> Any:
        i = idx.get(key.lower(), pos)
        return row[i] if i < len(row) else None

    waits: list[MetadataLockWait] = []
    for row in raw_rows:
        r: Any = row
        waits.append(
            MetadataLockWait(
                wait_age_secs=_int(_get(r, "wait_age_secs", 0)),
                object_schema=_str(_get(r, "object_schema", 1)),
                object_name=_str(_get(r, "object_name", 2)),
                waiting_pid=_int(_get(r, "waiting_pid", 3)),
                waiting_account=_str(_get(r, "waiting_account", 4)),
                waiting_lock_type=_str(_get(r, "waiting_lock_type", 5)),
                waiting_query=_str(_get(r, "waiting_query", 6)),
                blocking_pid=_int(_get(r, "blocking_pid", 7)),
                blocking_account=_str(_get(r, "blocking_account", 8)),
                blocking_lock_type=_str(_get(r, "blocking_lock_type", 9)),
            )
        )
    return waits
