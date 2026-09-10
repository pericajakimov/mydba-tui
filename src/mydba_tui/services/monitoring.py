"""
Monitoring service.

Backs the Monitoring screen — a lightweight, live "what's happening right now"
dashboard (not a PMM/Grafana replacement). Every metric is derived from a single
cheap ``SHOW GLOBAL STATUS`` snapshot plus a few global variables; rates
(queries/sec, bytes/sec, ...) are computed as the delta between two snapshots
divided by the elapsed wall-clock time.

All SQL is tagged and written to the SQL log. Snapshots are best-effort: a
failure yields an empty snapshot rather than raising, so the dashboard degrades
gracefully.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mydba_tui.logging import log_sql
from mydba_tui.services.sql_loader import tag_sql

if TYPE_CHECKING:
    from mysql.connector.abstracts import MySQLConnectionAbstract
    from mysql.connector.pooling import PooledMySQLConnection

    Connection = MySQLConnectionAbstract | PooledMySQLConnection


def _to_float(val: Any) -> float:
    """Coerce a status/variable value to float; 0.0 when not numeric."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


@dataclass(slots=True)
class Snapshot:
    """A point-in-time capture of global status counters and variables.

    Attributes:
        status: SHOW GLOBAL STATUS values, keyed by lowercased name (as float).
        variables: A few global variables, keyed by lowercased name (as string).
        taken_at: Wall-clock time (perf_counter) when the snapshot was taken,
            used as the denominator for rate calculations.
        available: False when the snapshot could not be read.
    """

    status: dict[str, float] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    taken_at: float = 0.0
    available: bool = True
    # InnoDB purge lag (trx_rseg_history_len); -1 when it couldn't be read.
    history_list_length: int = -1

    def gauge(self, name: str) -> float:
        """Return a status counter's current absolute value (0.0 if absent)."""
        return self.status.get(name.lower(), 0.0)

    def var(self, name: str) -> str:
        """Return a global variable's value ('' if absent)."""
        return self.variables.get(name.lower(), "")

    def var_float(self, name: str) -> float:
        """Return a global variable as float (0.0 if absent/non-numeric)."""
        return _to_float(self.variables.get(name.lower()))


# Global variables the dashboard needs alongside status counters. Read in one
# batched query rather than one round trip each.
_MONITOR_VARIABLES = (
    "max_connections",
    "innodb_buffer_pool_size",
    "innodb_page_size",
)


def fetch_snapshot(connection: Connection) -> Snapshot:
    """Capture global status + a few variables in one cheap pass.

    Best-effort: returns an unavailable snapshot on any error.

    Args:
        connection: Active MySQL connection.

    Returns:
        A Snapshot with status counters, selected variables, and a timestamp.
    """
    status = _fetch_status(connection)
    if status is None:
        return Snapshot(available=False, taken_at=time.perf_counter())
    variables = _fetch_variables(connection)
    return Snapshot(
        status=status,
        variables=variables,
        taken_at=time.perf_counter(),
        history_list_length=_fetch_history_list_length(connection),
    )


def _fetch_history_list_length(connection: Connection) -> int:
    """Read the InnoDB history list length (purge lag), best-effort.

    Sourced from information_schema.innodb_metrics (trx_rseg_history_len). The
    counter must be enabled to return a row; returns -1 when unavailable so the
    UI can show it as unknown rather than a misleading 0.
    """
    sql = tag_sql(
        "SELECT COUNT FROM information_schema.innodb_metrics WHERE NAME = 'trx_rseg_history_len'"
    )
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(sql)
        row: Any = cursor.fetchone()
        if row and row[0] is not None:
            return int(row[0])
        return -1
    except Exception:
        return -1
    finally:
        duration = time.perf_counter() - start
        log_sql(sql, duration, "monitoring.history_list")
        cursor.close()


def _fetch_status(connection: Connection) -> dict[str, float] | None:
    """Read all global status counters as a name->float map (None on error)."""
    sql = tag_sql("SHOW GLOBAL STATUS")
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        result: dict[str, float] = {}
        for row in rows:
            values = list(row)
            if len(values) >= 2 and values[0] is not None:
                result[str(values[0]).lower()] = _to_float(values[1])
        return result
    except Exception:
        return None
    finally:
        duration = time.perf_counter() - start
        log_sql(sql, duration, "monitoring.status")
        cursor.close()


def _fetch_variables(connection: Connection) -> dict[str, str]:
    """Read the monitoring variables in one batched query (best-effort)."""
    in_list = ", ".join(f"'{n}'" for n in _MONITOR_VARIABLES)
    sql = tag_sql(f"SHOW GLOBAL VARIABLES WHERE Variable_name IN ({in_list})")
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        result: dict[str, str] = {}
        for row in rows:
            values = list(row)
            if len(values) >= 2 and values[0] is not None:
                result[str(values[0]).lower()] = "" if values[1] is None else str(values[1])
        return result
    except Exception:
        return {}
    finally:
        duration = time.perf_counter() - start
        log_sql(sql, duration, "monitoring.variables")
        cursor.close()


def rate(prev: Snapshot, cur: Snapshot, name: str) -> float:
    """Per-second rate of a counter between two snapshots.

    Returns 0.0 when there is no usable interval or the counter went backwards
    (a server restart resets counters, which must not show as a huge spike).

    Args:
        prev: The earlier snapshot.
        cur: The later snapshot.
        name: Status counter name.

    Returns:
        The change per second, or 0.0 when it can't be computed.
    """
    elapsed = cur.taken_at - prev.taken_at
    if elapsed <= 0:
        return 0.0
    delta = cur.gauge(name) - prev.gauge(name)
    if delta < 0:
        return 0.0
    return delta / elapsed


def sum_rate(prev: Snapshot, cur: Snapshot, names: tuple[str, ...]) -> float:
    """Per-second rate of the sum of several counters (e.g. write commands)."""
    return sum(rate(prev, cur, n) for n in names)
