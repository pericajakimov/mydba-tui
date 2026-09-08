"""
Transactions service.

Reads active InnoDB transactions for the Administration Transactions view,
joined to the process list so each transaction carries its user, host, and
database. All SQL is written to the SQL log for transparency.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mydba_tui.logging import log_sql
from mydba_tui.services.processlist import _strip_port

if TYPE_CHECKING:
    from mysql.connector.abstracts import MySQLConnectionAbstract
    from mysql.connector.pooling import PooledMySQLConnection

# Columns presented, in display order.
TRANSACTION_COLUMNS = [
    "Trx ID",
    "Conn ID",
    "User",
    "Host",
    "DB",
    "State",
    "Age",
    "Rows Locked",
    "Query",
]

# innodb_trx joined to processlist for the session's user/host/db. Age is
# computed server-side as seconds since the transaction started.
_SQL_TRANSACTIONS = (
    "SELECT t.trx_id AS trx_id, "
    "t.trx_mysql_thread_id AS conn_id, "
    "p.USER AS user, p.HOST AS host, p.DB AS db, "
    "t.trx_state AS state, "
    "t.trx_started AS started, "
    "TIMESTAMPDIFF(SECOND, t.trx_started, NOW()) AS age_seconds, "
    "t.trx_rows_locked AS rows_locked, "
    "t.trx_query AS query "
    "FROM information_schema.innodb_trx t "
    "LEFT JOIN information_schema.processlist p "
    "ON p.ID = t.trx_mysql_thread_id "
    "ORDER BY age_seconds DESC"
)


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
class TransactionRow:
    """An active InnoDB transaction.

    Attributes:
        trx_id: InnoDB transaction id.
        conn_id: The connection/thread id running the transaction.
        user: MySQL user (from the process list; empty if unmatched).
        host: Client host IP (client source port stripped).
        db: Current database (may be empty).
        state: Transaction state (e.g. RUNNING, LOCK WAIT).
        started: Transaction start time as reported by the server.
        age_seconds: Seconds since the transaction started.
        rows_locked: Approximate number of rows locked.
        query: The statement currently running in the transaction (may be empty).
    """

    trx_id: str
    conn_id: int
    user: str
    host: str
    db: str
    state: str
    started: str
    age_seconds: int
    rows_locked: int
    query: str


def fetch_transactions(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> list[TransactionRow]:
    """Fetch active InnoDB transactions, oldest first.

    Args:
        connection: Active MySQL connection.

    Returns:
        List of TransactionRow sorted by age descending (longest-running first).
    """
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(_SQL_TRANSACTIONS)
        description = cursor.description or []
        col_names = [desc[0] for desc in description]
        raw_rows = cursor.fetchall()
    finally:
        duration = time.perf_counter() - start
        log_sql(_SQL_TRANSACTIONS, duration, "administration.transactions")
        cursor.close()

    idx = {name.lower(): i for i, name in enumerate(col_names)}

    def _get(row: Any, key: str, pos: int) -> Any:
        i = idx.get(key.lower(), pos)
        return row[i] if i < len(row) else None

    transactions: list[TransactionRow] = []
    for row in raw_rows:
        r: Any = row
        transactions.append(
            TransactionRow(
                trx_id=_str(_get(r, "trx_id", 0)),
                conn_id=_int(_get(r, "conn_id", 1)),
                user=_str(_get(r, "user", 2)),
                host=_strip_port(_str(_get(r, "host", 3))),
                db=_str(_get(r, "db", 4)),
                state=_str(_get(r, "state", 5)),
                started=_str(_get(r, "started", 6)),
                age_seconds=_int(_get(r, "age_seconds", 7)),
                rows_locked=_int(_get(r, "rows_locked", 8)),
                query=_str(_get(r, "query", 9)),
            )
        )
    return transactions


# Recent statements for a connection, from performance_schema. Ordered most
# recent first. TIMER values are picoseconds; converted to milliseconds.
_SQL_STATEMENT_HISTORY = (
    "SELECT h.SQL_TEXT AS sql_text, "
    "h.TIMER_WAIT / 1000000000 AS duration_ms, "
    "h.EVENT_ID AS event_id "
    "FROM performance_schema.events_statements_history h "
    "JOIN performance_schema.threads t ON t.THREAD_ID = h.THREAD_ID "
    "WHERE t.PROCESSLIST_ID = %s AND h.SQL_TEXT IS NOT NULL "
    "ORDER BY h.EVENT_ID DESC "
    "LIMIT 20"
)


@dataclass(slots=True)
class StatementHistoryEntry:
    """A single statement from a connection's recent history.

    Attributes:
        sql: The statement text.
        duration_ms: Statement duration in milliseconds (0 if unknown).
    """

    sql: str
    duration_ms: float


def fetch_statement_history(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    conn_id: int,
) -> list[StatementHistoryEntry]:
    """Fetch recent statements for a connection from performance_schema.

    Best-effort: returns an empty list if performance_schema statement history
    is unavailable or disabled (e.g. on MariaDB or when the consumer is off).

    Args:
        connection: Active MySQL connection.
        conn_id: The connection/processlist id whose history to fetch.

    Returns:
        Recent statements, most recent first (capped), or [] if unavailable.
    """
    if conn_id <= 0:
        return []

    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(_SQL_STATEMENT_HISTORY, (conn_id,))
        raw_rows = cursor.fetchall()
    except Exception:
        raw_rows = []
    finally:
        duration = time.perf_counter() - start
        log_sql(_SQL_STATEMENT_HISTORY, duration, "administration.statement_history")
        cursor.close()

    entries: list[StatementHistoryEntry] = []
    for row in raw_rows:
        r: Any = row
        sql = _str(r[0]) if len(r) > 0 else ""
        if not sql.strip():
            continue
        raw_ms = r[1] if len(r) > 1 else 0
        try:
            duration_ms = float(raw_ms) if raw_ms is not None else 0.0
        except (ValueError, TypeError):
            duration_ms = 0.0
        entries.append(StatementHistoryEntry(sql=sql, duration_ms=duration_ms))
    return entries
