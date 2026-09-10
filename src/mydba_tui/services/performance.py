"""
Performance diagnostics service (sys schema).

Backs the Administration → Performance tab. The MySQL ``sys`` schema packages
raw performance_schema data into human-readable diagnostic views. Each subject
(statements, users, hosts, waits, I/O, tables, indexes, memory) comes as a
family: a summary view plus several ``_by_*`` breakdown views keyed on the same
subject. This service exposes them uniformly:

- ``fetch_view`` runs a summary view file and returns ``(columns, rows)`` so the
  UI can render any sys view as a generic grid.
- ``fetch_breakdown`` runs a keyed breakdown view file (parameterized) for a
  drill-down detail.

All SQL lives in ``sql/admin/perf/``, is tagged with the mydba marker, and is
written to the SQL log. Every call is best-effort: the sys schema is absent on
MariaDB and some views need performance_schema consumers enabled, so a missing
view or privilege yields empty data rather than an error.
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

    Connection = MySQLConnectionAbstract | PooledMySQLConnection


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


@dataclass(slots=True)
class GridData:
    """A generic result grid: column headers plus string-coerced rows.

    Attributes:
        columns: Column display names, in order.
        rows: Row values as display strings, aligned to ``columns``.
        available: False when the source view could not be read (e.g. the sys
            schema is absent, as on MariaDB, or a privilege is missing).
    """

    columns: list[str]
    rows: list[list[str]]
    available: bool = True

    @property
    def empty(self) -> bool:
        """True when there are no rows (regardless of availability)."""
        return not self.rows


def fetch_view(connection: Connection, sql_file: str, source: str) -> GridData:
    """Run a sys-schema summary view file and return it as a generic grid.

    Best-effort: any error (missing view/privilege) yields an unavailable grid.

    Args:
        connection: Active MySQL connection.
        sql_file: Path under ``sql/`` (e.g. ``admin/perf/statement_analysis.sql``).
        source: SQL-log source label.

    Returns:
        A GridData with columns and string rows, or an unavailable grid.
    """
    sql = load_sql(sql_file)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(sql)
        description = cursor.description or []
        columns = [d[0] for d in description]
        raw = cursor.fetchall()
        rows = [[_str(v) for v in row] for row in raw]
        return GridData(columns=columns, rows=rows, available=True)
    except Exception:
        return GridData(columns=[], rows=[], available=False)
    finally:
        duration = time.perf_counter() - start
        log_sql(sql, duration, source)
        cursor.close()


def fetch_breakdown(
    connection: Connection,
    sql_file: str,
    params: tuple[Any, ...],
    source: str,
) -> GridData:
    """Run a keyed breakdown view file (parameterized) and return a grid.

    Args:
        connection: Active MySQL connection.
        sql_file: Path under ``sql/`` to a breakdown query with ``%s`` markers.
        params: Parameters bound to the query (e.g. the selected user/host).
        source: SQL-log source label.

    Returns:
        A GridData, or an unavailable grid on any error.
    """
    sql = load_sql(sql_file)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(sql, params)
        description = cursor.description or []
        columns = [d[0] for d in description]
        raw = cursor.fetchall()
        rows = [[_str(v) for v in row] for row in raw]
        return GridData(columns=columns, rows=rows, available=True)
    except Exception:
        return GridData(columns=[], rows=[], available=False)
    finally:
        duration = time.perf_counter() - start
        log_sql(sql, duration, source)
        cursor.close()


@dataclass(slots=True)
class StatementDigestSample:
    """The full text and sample for a statement digest (Top Queries detail)."""

    digest_text: str
    sample_text: str
    schema_name: str
    exec_count: str
    first_seen: str
    last_seen: str


def fetch_statement_digest_sample(
    connection: Connection, digest: str
) -> StatementDigestSample | None:
    """Fetch the full normalized text and a sample for a statement digest.

    Best-effort: returns None if unavailable.

    Args:
        connection: Active MySQL connection.
        digest: The statement digest (stable key from statement_analysis).

    Returns:
        A StatementDigestSample, or None when the row cannot be read.
    """
    grid = fetch_breakdown(
        connection,
        "admin/perf/statement_digest_sample.sql",
        (digest,),
        "administration.performance.statement_sample",
    )
    if not grid.available or not grid.rows:
        return None
    idx = {c.lower(): i for i, c in enumerate(grid.columns)}
    row = grid.rows[0]

    def col(name: str) -> str:
        i = idx.get(name.lower())
        return row[i] if i is not None and i < len(row) else ""

    return StatementDigestSample(
        digest_text=col("digest_text"),
        sample_text=col("sample_text"),
        schema_name=col("schema_name"),
        exec_count=col("exec_count"),
        first_seen=col("first_seen"),
        last_seen=col("last_seen"),
    )
