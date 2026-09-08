"""
Lock waits service.

Reads InnoDB row-lock blocking information for the Administration Locks view,
showing which session is blocked and which session is blocking it. Sourced from
the sys schema (sys.innodb_lock_waits), enriched with user/host from the process
list. All SQL is written to the SQL log for transparency.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mydba_tui.logging import log_sql
from mydba_tui.services.processlist import _strip_port
from mydba_tui.services.sql_loader import load_sql

if TYPE_CHECKING:
    from mysql.connector.abstracts import MySQLConnectionAbstract
    from mysql.connector.pooling import PooledMySQLConnection

# Columns presented, in display order.
LOCK_COLUMNS = [
    "Wait Age",
    "Locked Table",
    "Waiting PID",
    "Waiting User",
    "Waiting Query",
    "Blocking PID",
    "Blocking User",
    "Blocking Query",
]

_SQL_FILE_LOCK_WAITS = "admin/lock_waits.sql"


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
class LockWait:
    """A single InnoDB lock-wait relationship (a blocked/blocking pair).

    Attributes:
        wait_age_secs: Seconds the waiting session has been blocked.
        locked_schema: Schema of the locked table.
        locked_table: Name of the locked table.
        locked_type: Type of the waiting lock (e.g. RECORD).
        waiting_pid: Processlist id of the blocked session.
        waiting_user: User of the blocked session.
        waiting_host: Client host (IP) of the blocked session.
        waiting_lock_mode: Lock mode the blocked session requested.
        waiting_query: Statement the blocked session is waiting on.
        blocking_pid: Processlist id of the blocking session.
        blocking_user: User of the blocking session.
        blocking_host: Client host (IP) of the blocking session.
        blocking_lock_mode: Lock mode held by the blocking session.
        blocking_query: Statement the blocking session ran (empty if idle).
    """

    wait_age_secs: int
    locked_schema: str
    locked_table: str
    locked_type: str
    waiting_pid: int
    waiting_user: str
    waiting_host: str
    waiting_lock_mode: str
    waiting_query: str
    blocking_pid: int
    blocking_user: str
    blocking_host: str
    blocking_lock_mode: str
    blocking_query: str


def fetch_lock_waits(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> list[LockWait]:
    """Fetch InnoDB lock waits, longest-waiting first.

    Best-effort: returns an empty list if the sys schema view is unavailable
    (e.g. on MariaDB or when the sys schema is not installed).

    Args:
        connection: Active MySQL connection.

    Returns:
        List of LockWait sorted by wait age descending, or [] if unavailable.
    """
    sql = load_sql(_SQL_FILE_LOCK_WAITS)
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
        log_sql(sql, duration, "administration.locks")
        cursor.close()

    idx = {name.lower(): i for i, name in enumerate(col_names)}

    def _get(row: Any, key: str, pos: int) -> Any:
        i = idx.get(key.lower(), pos)
        return row[i] if i < len(row) else None

    waits: list[LockWait] = []
    for row in raw_rows:
        r: Any = row
        waits.append(
            LockWait(
                wait_age_secs=_int(_get(r, "wait_age_secs", 0)),
                locked_schema=_str(_get(r, "locked_schema", 1)),
                locked_table=_str(_get(r, "locked_table", 2)),
                locked_type=_str(_get(r, "locked_type", 3)),
                waiting_pid=_int(_get(r, "waiting_pid", 4)),
                waiting_user=_str(_get(r, "waiting_user", 5)),
                waiting_host=_strip_port(_str(_get(r, "waiting_host", 6))),
                waiting_lock_mode=_str(_get(r, "waiting_lock_mode", 7)),
                waiting_query=_str(_get(r, "waiting_query", 8)),
                blocking_pid=_int(_get(r, "blocking_pid", 9)),
                blocking_user=_str(_get(r, "blocking_user", 10)),
                blocking_host=_strip_port(_str(_get(r, "blocking_host", 11))),
                blocking_lock_mode=_str(_get(r, "blocking_lock_mode", 12)),
                blocking_query=_str(_get(r, "blocking_query", 13)),
            )
        )
    return waits
