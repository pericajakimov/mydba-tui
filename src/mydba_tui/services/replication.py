"""
Replication service.

Gathers a unified, read-only view of replication for the Administration
Replication tab: async replica channels (SHOW REPLICA STATUS), the primary /
binlog state (SHOW REPLICAS, binary log status), GTID state, and Galera/wsrep
cluster state. A server may be several of these at once (e.g. a PXC node that
is also an async replica), so each part is filled only when it applies.

All SQL is tagged and written to the SQL log. Every query is best-effort:
a missing privilege or unsupported feature yields empty data, never an error.
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

    from mydba_tui.server import ServerInfo


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


def _int_or_none(val: Any) -> int | None:
    """Coerce to int, or None if not a number (e.g. NULL Seconds_Behind)."""
    if val is None or val == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


@dataclass(slots=True)
class ReplicaChannel:
    """One replication channel's status (from SHOW REPLICA STATUS).

    Attributes:
        channel: Channel name ('' for the default channel).
        io_running: Replica_IO_Running value (Yes/No/Connecting).
        sql_running: Replica_SQL_Running value (Yes/No).
        seconds_behind: Seconds_Behind_Source (None when NULL / not replicating).
        source_host: Source host.
        source_port: Source port.
        source_log_file: Source binlog file the IO thread is reading.
        read_source_log_pos: Position read from the source binlog.
        relay_source_log_file: Source binlog file the SQL thread has applied.
        exec_source_log_pos: Source binlog position the SQL thread has applied.
        relay_log_file: Current relay log file.
        relay_log_pos: Current relay log position.
        relay_log_space: Total size of all relay logs, in bytes.
        retrieved_gtid_set: GTIDs received.
        executed_gtid_set: GTIDs executed.
        auto_position: Whether GTID auto-positioning is on.
        parallel_workers: Configured parallel applier workers (0 = single-thread).
        parallel_type: Parallel applier type (e.g. LOGICAL_CLOCK).
        busy_workers: Applier workers currently applying a transaction.
        last_io_error: Last IO thread error (empty if none).
        last_sql_error: Last SQL thread error (empty if none).
        last_io_errno: Last IO thread errno.
        last_sql_errno: Last SQL thread errno.
    """

    channel: str
    io_running: str
    sql_running: str
    seconds_behind: int | None
    source_host: str
    source_port: str
    source_log_file: str
    read_source_log_pos: str
    relay_source_log_file: str
    exec_source_log_pos: str
    relay_log_file: str
    relay_log_pos: str
    relay_log_space: int
    retrieved_gtid_set: str
    executed_gtid_set: str
    auto_position: bool
    parallel_workers: int
    parallel_type: str
    busy_workers: int
    last_io_error: str
    last_sql_error: str
    last_io_errno: str
    last_sql_errno: str

    @property
    def healthy(self) -> bool:
        """True if both threads are running."""
        return self.io_running.lower() == "yes" and self.sql_running.lower() == "yes"

    @property
    def has_error(self) -> bool:
        """True if either thread reports an error."""
        return bool(self.last_io_error.strip() or self.last_sql_error.strip())

    @property
    def unapplied_bytes(self) -> int | None:
        """Bytes retrieved from the source but not yet applied.

        This is the gap between what the IO thread has read from the source
        binlog (Read_Source_Log_Pos) and what the SQL thread has applied
        (Exec_Source_Log_Pos). It is only meaningful while both positions
        refer to the same source binlog file; when the applier trails onto an
        earlier file the byte gap spans files and can't be derived from
        positions alone, so this returns None.
        """
        if self.source_log_file and self.source_log_file == self.relay_source_log_file:
            try:
                gap = int(self.read_source_log_pos) - int(self.exec_source_log_pos)
            except (ValueError, TypeError):
                return None
            return max(gap, 0)
        return None


@dataclass(slots=True)
class ReplicaRow:
    """A replica connected to this server, from SHOW REPLICAS."""

    server_id: str
    host: str
    port: str


@dataclass(slots=True)
class PrimaryInfo:
    """Binary log / primary state.

    Attributes:
        binlog_file: Current binary log file.
        binlog_pos: Current binary log position.
        binlog_format: Binary log format (ROW/STATEMENT/MIXED).
        binlog_row_image: binlog_row_image (FULL/MINIMAL/NOBLOB) — how much of
            each row is logged for ROW events.
        binlog_row_metadata: binlog_row_metadata (MINIMAL/FULL) — how much
            table metadata is written with row events.
        binlog_count: Number of binary logs.
        binlog_total_bytes: Total size of binary logs in bytes.
        replicas: Replicas connected to this server.
    """

    binlog_file: str = ""
    binlog_pos: str = ""
    binlog_format: str = ""
    binlog_row_image: str = ""
    binlog_row_metadata: str = ""
    binlog_count: int = 0
    binlog_total_bytes: int = 0
    replicas: list[ReplicaRow] = field(default_factory=list)

    @property
    def is_primary(self) -> bool:
        """True if this server has connected replicas."""
        return bool(self.replicas)


@dataclass(slots=True)
class GtidInfo:
    """GTID state.

    Attributes:
        enabled: Whether GTID mode is on.
        executed: gtid_executed set.
        purged: gtid_purged set.
        retrieved: GTIDs retrieved by replica channels (union across channels).
    """

    enabled: bool = False
    executed: str = ""
    purged: str = ""
    retrieved: str = ""


@dataclass(slots=True)
class ClusterInfo:
    """Galera / PXC cluster state (wsrep).

    Attributes:
        enabled: Whether wsrep is active.
        cluster_name: Cluster name.
        cluster_size: Number of nodes.
        cluster_status: Cluster status (e.g. Primary).
        local_state: Local node state comment (e.g. Synced).
        flow_control_paused: Fraction of time paused by flow control.
    """

    enabled: bool = False
    cluster_name: str = ""
    cluster_size: str = ""
    cluster_status: str = ""
    local_state: str = ""
    flow_control_paused: str = ""


@dataclass(slots=True)
class ReplicationInfo:
    """Aggregated replication state for the connected server."""

    channels: list[ReplicaChannel] = field(default_factory=list)
    primary: PrimaryInfo = field(default_factory=PrimaryInfo)
    gtid: GtidInfo = field(default_factory=GtidInfo)
    cluster: ClusterInfo = field(default_factory=ClusterInfo)

    @property
    def is_replica(self) -> bool:
        """True if the server has at least one replica channel."""
        return bool(self.channels)


# --- Query helpers ---


def _rows_as_dicts(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    sql: str,
    source: str,
) -> list[dict[str, Any]]:
    """Run a SHOW/SELECT and return rows as dicts keyed by column name.

    Best-effort: returns an empty list on any error.
    """
    tagged = tag_sql(sql)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(tagged)
        description = cursor.description or []
        cols = [d[0] for d in description]
        raw = cursor.fetchall()
        result = [dict(zip(cols, row, strict=False)) for row in raw]
    except Exception:
        result = []
    finally:
        duration = time.perf_counter() - start
        log_sql(tagged, duration, source)
        cursor.close()
    return result


# Global variables read for the replication view — fetched in a single query
# rather than one round trip each (per-variable SHOW ... LIKE is slow).
_REPL_VARIABLES = (
    "replica_parallel_workers",
    "replica_parallel_type",
    "binlog_format",
    "binlog_row_image",
    "binlog_row_metadata",
    "gtid_mode",
    "gtid_executed",
    "gtid_purged",
    "wsrep_provider",
    "wsrep_on",
    "wsrep_cluster_name",
)

# Global status counters read for the cluster section — also one query.
_REPL_STATUS = (
    "wsrep_cluster_size",
    "wsrep_cluster_status",
    "wsrep_local_state_comment",
    "wsrep_flow_control_paused",
)


def _name_value_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    """Turn Variable_name/Value (or name/value) rows into a lowercased map."""
    result: dict[str, str] = {}
    for row in rows:
        values = list(row.values())
        if len(values) >= 2:
            result[_str(values[0]).lower()] = _str(values[1])
    return result


def _in_list(names: tuple[str, ...]) -> str:
    """Build a quoted, comma-separated IN-list from variable names."""
    return ", ".join(f"'{n}'" for n in names)


def _fetch_variables(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    names: tuple[str, ...],
) -> dict[str, str]:
    """Read many global variables in one query (keyed by lowercased name).

    Uses ``SHOW GLOBAL VARIABLES WHERE Variable_name IN (...)`` so all values
    come back in a single round trip instead of one query per variable. This
    form is supported on every MySQL/MariaDB version, so there is no fallback:
    an empty result simply means none of the requested variables exist (e.g.
    the wsrep_* variables on a non-Galera server), which is not an error.
    """
    rows = _rows_as_dicts(
        connection,
        f"SHOW GLOBAL VARIABLES WHERE Variable_name IN ({_in_list(names)})",
        "administration.replication.vars",
    )
    return _name_value_map(rows)


def _fetch_status(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    names: tuple[str, ...],
) -> dict[str, str]:
    """Read many global status counters in one query (keyed by lowercased name).

    ``SHOW GLOBAL STATUS`` is supported everywhere, so there is no fallback: an
    empty result (e.g. the wsrep_* counters are absent on a non-Galera server)
    is expected and simply yields an empty map.
    """
    rows = _rows_as_dicts(
        connection,
        f"SHOW GLOBAL STATUS WHERE Variable_name IN ({_in_list(names)})",
        "administration.replication.status",
    )
    return _name_value_map(rows)


def _get(row: dict[str, Any], key: str) -> Any:
    """Case-insensitive lookup in a result-row dict."""
    if key in row:
        return row[key]
    lowered = {k.lower(): v for k, v in row.items()}
    return lowered.get(key.lower())


# --- Fetch ---


def fetch_replication(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    server_info: ServerInfo | None = None,
) -> ReplicationInfo:
    """Gather the full replication picture for the connected server.

    Args:
        connection: Active MySQL connection.
        server_info: Detected server info (used only for vendor hints; the
            actual state is always read live).

    Returns:
        A populated ReplicationInfo (sections empty where not applicable).
    """
    # Read all global variables in one query (rather than one round trip per
    # name) and share the map across the sub-fetchers. The wsrep_* status
    # counters are fetched lazily inside _fetch_cluster, and only on an actual
    # cluster node, so a plain server never runs the status query.
    variables = _fetch_variables(connection, _REPL_VARIABLES)

    info = ReplicationInfo()
    info.channels = _fetch_channels(connection, variables)
    info.primary = _fetch_primary(connection, variables)
    info.gtid = _fetch_gtid(variables)
    info.cluster = _fetch_cluster(connection, variables)

    # Retrieved GTIDs live on the replica channels; surface their union in the
    # GTID section for a complete picture.
    retrieved = [c.retrieved_gtid_set for c in info.channels if c.retrieved_gtid_set.strip()]
    if retrieved:
        info.gtid.retrieved = ",\n".join(retrieved)

    return info


def _fetch_channels(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    variables: dict[str, str],
) -> list[ReplicaChannel]:
    """Read replica channels from SHOW REPLICA STATUS (one row per channel)."""
    rows = _rows_as_dicts(connection, "SHOW REPLICA STATUS", "administration.replication.replica")
    if not rows:
        return []

    # Applier configuration is server-global; read from the shared var map.
    parallel_workers = _int_or_none(variables.get("replica_parallel_workers")) or 0
    parallel_type = variables.get("replica_parallel_type", "")
    busy_by_channel = _busy_workers_by_channel(connection)

    channels: list[ReplicaChannel] = []
    for row in rows:
        channel_name = _str(_get(row, "Channel_Name"))
        channels.append(
            ReplicaChannel(
                channel=channel_name,
                io_running=_str(_get(row, "Replica_IO_Running")),
                sql_running=_str(_get(row, "Replica_SQL_Running")),
                seconds_behind=_int_or_none(_get(row, "Seconds_Behind_Source")),
                source_host=_str(_get(row, "Source_Host")),
                source_port=_str(_get(row, "Source_Port")),
                source_log_file=_str(_get(row, "Source_Log_File")),
                read_source_log_pos=_str(_get(row, "Read_Source_Log_Pos")),
                relay_source_log_file=_str(_get(row, "Relay_Source_Log_File")),
                exec_source_log_pos=_str(_get(row, "Exec_Source_Log_Pos")),
                relay_log_file=_str(_get(row, "Relay_Log_File")),
                relay_log_pos=_str(_get(row, "Relay_Log_Pos")),
                relay_log_space=_int_or_none(_get(row, "Relay_Log_Space")) or 0,
                retrieved_gtid_set=_str(_get(row, "Retrieved_Gtid_Set")),
                executed_gtid_set=_str(_get(row, "Executed_Gtid_Set")),
                auto_position=_str(_get(row, "Auto_Position")) in ("1", "ON"),
                parallel_workers=parallel_workers,
                parallel_type=parallel_type,
                busy_workers=busy_by_channel.get(channel_name, 0),
                last_io_error=_str(_get(row, "Last_IO_Error")),
                last_sql_error=_str(_get(row, "Last_SQL_Error")),
                last_io_errno=_str(_get(row, "Last_IO_Errno")),
                last_sql_errno=_str(_get(row, "Last_SQL_Errno")),
            )
        )
    return channels


def _busy_workers_by_channel(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> dict[str, int]:
    """Count applier workers currently applying a transaction, per channel.

    Best-effort via performance_schema.replication_applier_status_by_worker;
    returns an empty map when unavailable.
    """
    rows = _rows_as_dicts(
        connection,
        "SELECT CHANNEL_NAME AS ch, COUNT(*) AS busy "
        "FROM performance_schema.replication_applier_status_by_worker "
        "WHERE APPLYING_TRANSACTION <> '' "
        "GROUP BY CHANNEL_NAME",
        "administration.replication.workers",
    )
    result: dict[str, int] = {}
    for row in rows:
        result[_str(_get(row, "ch"))] = _int_or_none(_get(row, "busy")) or 0
    return result


def _fetch_primary(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    variables: dict[str, str],
) -> PrimaryInfo:
    """Read binlog state and connected replicas."""
    primary = PrimaryInfo()

    # Connected replicas.
    for row in _rows_as_dicts(connection, "SHOW REPLICAS", "administration.replication.replicas"):
        primary.replicas.append(
            ReplicaRow(
                server_id=_str(_get(row, "Server_Id")),
                host=_str(_get(row, "Host")),
                port=_str(_get(row, "Port")),
            )
        )

    # Current binary log status. MySQL 8.4 renamed SHOW MASTER STATUS to
    # SHOW BINARY LOG STATUS; try the new form first, fall back to the old.
    status_rows = _rows_as_dicts(
        connection, "SHOW BINARY LOG STATUS", "administration.replication.binlog_status"
    )
    if not status_rows:
        status_rows = _rows_as_dicts(
            connection, "SHOW MASTER STATUS", "administration.replication.binlog_status"
        )
    if status_rows:
        primary.binlog_file = _str(_get(status_rows[0], "File"))
        primary.binlog_pos = _str(_get(status_rows[0], "Position"))

    primary.binlog_format = variables.get("binlog_format", "")
    primary.binlog_row_image = variables.get("binlog_row_image", "")
    primary.binlog_row_metadata = variables.get("binlog_row_metadata", "")

    # Binary log inventory.
    logs = _rows_as_dicts(connection, "SHOW BINARY LOGS", "administration.replication.binlogs")
    primary.binlog_count = len(logs)
    total = 0
    for row in logs:
        size = _get(row, "File_size")
        try:
            total += int(size) if size is not None else 0
        except (ValueError, TypeError):
            pass
    primary.binlog_total_bytes = total

    return primary


def _fetch_gtid(variables: dict[str, str]) -> GtidInfo:
    """Read GTID mode and executed/purged sets from the shared var map."""
    gtid = GtidInfo()
    mode = variables.get("gtid_mode", "")
    gtid.enabled = mode.upper() in ("ON", "ON_PERMISSIVE")
    if gtid.enabled:
        gtid.executed = variables.get("gtid_executed", "")
        gtid.purged = variables.get("gtid_purged", "")
    return gtid


def _fetch_cluster(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    variables: dict[str, str],
) -> ClusterInfo:
    """Read Galera/PXC wsrep cluster state (empty when not a cluster node).

    Whether this is a cluster node is decided from the wsrep_* variables we
    already have. The wsrep_* status counters are only queried when it is a
    cluster node, so a plain (non-Galera) server pays nothing extra here.
    """
    cluster = ClusterInfo()
    provider = variables.get("wsrep_provider", "")
    wsrep_on = variables.get("wsrep_on", "")
    if not provider or provider.lower() in ("none", "") or wsrep_on.upper() == "OFF":
        return cluster
    cluster.enabled = True
    cluster.cluster_name = variables.get("wsrep_cluster_name", "")
    status = _fetch_status(connection, _REPL_STATUS)
    cluster.cluster_size = status.get("wsrep_cluster_size", "")
    cluster.cluster_status = status.get("wsrep_cluster_status", "")
    cluster.local_state = status.get("wsrep_local_state_comment", "")
    cluster.flow_control_paused = status.get("wsrep_flow_control_paused", "")
    return cluster


# --- Health verdict (interpretation, kept in Python) ---

# Lag (seconds) at or above which a running replica is flagged as lagging.
LAG_WARN_SECONDS = 30


@dataclass(slots=True)
class HealthVerdict:
    """A one-line, colour-coded health summary for the banner.

    Attributes:
        level: One of "healthy", "warn", "error", "info".
        text: The message to display.
    """

    level: str
    text: str


def compute_verdict(info: ReplicationInfo) -> HealthVerdict:
    """Summarize replication state into a single banner verdict.

    Priority: a broken replica thread is the most urgent thing to surface,
    then lag, then healthy replication, then primary/cluster/standalone.
    """
    # Broken replica threads take top priority.
    for ch in info.channels:
        if ch.has_error or not ch.healthy:
            label = f"channel '{ch.channel}'" if ch.channel else "replica"
            err = ch.last_sql_error or ch.last_io_error
            errno = ch.last_sql_errno if ch.last_sql_error else ch.last_io_errno
            detail = f": {errno} {err}" if err else " stopped"
            return HealthVerdict("error", f"BROKEN — {label}{detail}")

    # Running replica(s): report the worst lag.
    if info.channels:
        lags = [c.seconds_behind for c in info.channels if c.seconds_behind is not None]
        worst = max(lags) if lags else None
        if worst is not None and worst >= LAG_WARN_SECONDS:
            return HealthVerdict("warn", f"LAGGING — {worst}s behind source")
        behind = f"{worst}s behind" if worst is not None else "lag unknown"
        n = len(info.channels)
        chans = f"{n} channel{'s' if n != 1 else ''}"
        return HealthVerdict("healthy", f"HEALTHY — {chans} running, {behind}")

    # Galera cluster node.
    if info.cluster.enabled:
        synced = info.cluster.local_state.lower() == "synced"
        level = "healthy" if synced else "warn"
        return HealthVerdict(
            level,
            f"GALERA — {info.cluster.local_state or 'unknown'} "
            f"({info.cluster.cluster_size or '?'} nodes)",
        )

    # Primary with connected replicas.
    if info.primary.is_primary:
        n = len(info.primary.replicas)
        return HealthVerdict("info", f"PRIMARY — {n} replica{'s' if n != 1 else ''} connected")

    return HealthVerdict("info", "STANDALONE — no replication configured")


def lag_trend(samples: list[int]) -> str:
    """Return a trend arrow for a series of lag samples (newest last)."""
    if len(samples) < 2:
        return "—"
    if samples[-1] > samples[-2]:
        return "▲"
    if samples[-1] < samples[-2]:
        return "▼"
    return "—"
