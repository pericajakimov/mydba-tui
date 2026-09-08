"""
Process list service.

Provides a live view of active MySQL sessions and the ability to terminate
them. The query source is chosen based on the detected server so the columns
are consistent across MySQL, Percona, PXC, Aurora, and MariaDB.

All SQL executed here is written to the SQL log for transparency.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mydba_tui.logging import log_sql
from mydba_tui.services.sql_loader import load_sql, tag_sql

if TYPE_CHECKING:
    from mysql.connector.abstracts import MySQLConnectionAbstract
    from mysql.connector.pooling import PooledMySQLConnection

    from mydba_tui.server import ServerInfo

# Columns presented in the process list, in display order. These names match
# the aliases used by the queries below so every backend yields the same shape.
PROCESS_COLUMNS = [
    "Id",
    "User",
    "Host",
    "db",
    "Command",
    "Time",
    "State",
    "Program",
    "Info",
]

# Query sources by backend. The two substantial queries live in sql/admin/;
# the universal fallback is a trivial statement kept inline.
_SQL_FILE_PERFORMANCE_SCHEMA = "admin/processlist_performance_schema.sql"
_SQL_FILE_INFORMATION_SCHEMA = "admin/processlist_information_schema.sql"
_SQL_SHOW = tag_sql("SHOW FULL PROCESSLIST")


@dataclass(slots=True)
class ProcessRow:
    """A single session in the process list.

    Attributes:
        id: Connection/thread id.
        user: MySQL user.
        host: Client host IP (client source port stripped).
        db: Current database (may be empty/None).
        command: Command type (e.g. Query, Sleep).
        time: Seconds in the current state.
        state: Thread state.
        program: Client program name (empty when the server can't report it).
        info: The current statement text (may be empty/None).
    """

    id: int
    user: str
    host: str
    db: str
    command: str
    time: int
    state: str
    program: str
    info: str

    def as_cells(self) -> list[Any]:
        """Return values in PROCESS_COLUMNS order for table rendering."""
        return [
            self.id,
            self.user,
            self.host,
            self.db,
            self.command,
            self.time,
            self.state,
            self.program,
            self.info,
        ]


def _version_major_minor(version: str) -> tuple[int, int]:
    """Parse a version string into (major, minor). Returns (0, 0) on failure."""
    parts = version.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        return (0, 0)
    return (major, minor)


def select_processlist_query(server_info: ServerInfo | None) -> str:
    """Choose the process list query based on the detected server.

    - MariaDB → information_schema.PROCESSLIST
    - MySQL family (oracle/percona/pxc/aurora) 8.0+ → performance_schema
    - Anything else (unknown vendor/version) → SHOW FULL PROCESSLIST

    Args:
        server_info: Detected server information, or None if unknown.

    Returns:
        The SQL statement to run.
    """
    if server_info is None:
        return _SQL_SHOW

    vendor = server_info.vendor
    if vendor == "mariadb":
        return load_sql(_SQL_FILE_INFORMATION_SCHEMA)

    if vendor in ("oracle", "percona", "pxc", "aurora"):
        major, minor = _version_major_minor(server_info.version)
        if (major, minor) >= (8, 0):
            return load_sql(_SQL_FILE_PERFORMANCE_SCHEMA)
        # Older MySQL family without a usable performance_schema.processlist.
        return _SQL_SHOW

    return _SQL_SHOW


def fetch_processes(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    server_info: ServerInfo | None,
) -> list[ProcessRow]:
    """Fetch the current process list.

    Args:
        connection: Active MySQL connection.
        server_info: Detected server information (drives query selection).

    Returns:
        List of ProcessRow, ordered by time descending.
    """
    sql = select_processlist_query(server_info)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(sql)
        description = cursor.description or []
        col_names = [desc[0] for desc in description]
        raw_rows = cursor.fetchall()
    finally:
        duration = time.perf_counter() - start
        log_sql(sql, duration, "administration.processlist")
        cursor.close()

    # Map columns by name (case-insensitive). SHOW FULL PROCESSLIST has no
    # Program column, so its name lookup misses; the fallback positions are the
    # perf_schema/information_schema layout, and Program's fallback (8) is out
    # of range for SHOW (8 columns), yielding None there rather than Info.
    idx = {name.lower(): i for i, name in enumerate(col_names)}

    def _get(row: Any, key: str, pos: int) -> Any:
        i = idx.get(key.lower(), pos)
        return row[i] if i < len(row) else None

    processes: list[ProcessRow] = []
    for row in raw_rows:
        raw_id = _get(row, "Id", 0)
        raw_time = _get(row, "Time", 5)
        processes.append(
            ProcessRow(
                id=int(raw_id) if raw_id is not None else 0,
                user=_str(_get(row, "User", 1)),
                host=_strip_port(_str(_get(row, "Host", 2))),
                db=_str(_get(row, "db", 3)),
                command=_str(_get(row, "Command", 4)),
                time=int(raw_time) if raw_time is not None else 0,
                state=_str(_get(row, "State", 6)),
                program=_str(_get(row, "Program", 8)),
                info=_str(_get(row, "Info", 7)),
            )
        )
    return processes


def _strip_port(host: str) -> str:
    """Strip the client source port from a host string.

    MySQL reports client hosts as ``ip:port`` (e.g. ``10.0.0.1:53344``). We
    only care about the IP/hostname. IPv6 addresses contain colons, so only a
    trailing ``:<digits>`` segment is removed.

    Args:
        host: Host string as reported by the server.

    Returns:
        The host without the trailing client port.
    """
    if not host:
        return host
    # Bracketed IPv6 with port: [::1]:3306 -> ::1
    if host.startswith("[") and "]" in host:
        return host[1 : host.index("]")]
    # More than one colon and no brackets → bare IPv6 address, leave as-is.
    if host.count(":") > 1:
        return host
    sep = host.rfind(":")
    if sep == -1:
        return host
    port_part = host[sep + 1 :]
    if port_part.isdigit():
        return host[:sep]
    return host


def _str(val: Any) -> str:
    """Coerce a possibly-None value to a display string."""
    if val is None:
        return ""
    if isinstance(val, (bytes, bytearray)):
        try:
            return val.decode("utf-8", "replace")
        except Exception:
            return str(val)
    return str(val)


def kill_session(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    process_id: int,
    *,
    query_only: bool,
) -> None:
    """Terminate a session or just its current query.

    Args:
        connection: Active MySQL connection.
        process_id: The connection/thread id to target.
        query_only: If True, run ``KILL QUERY`` (cancels the running statement
            but keeps the connection); otherwise ``KILL`` (drops the
            connection).

    Raises:
        Exception: Propagates database errors (e.g. unknown thread id) to the
            caller so they can be surfaced to the user.
    """
    sql = tag_sql(f"KILL {'QUERY ' if query_only else ''}{int(process_id)}")
    start = time.perf_counter()
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
    finally:
        duration = time.perf_counter() - start
        log_sql(sql, duration, "administration.kill")
        cursor.close()
