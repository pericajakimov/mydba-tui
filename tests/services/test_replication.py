"""Tests for the replication service (verdict, trend, and fetch mapping)."""

from typing import Any

from mydba_tui.services.replication import (
    ClusterInfo,
    PrimaryInfo,
    ReplicaChannel,
    ReplicaRow,
    ReplicationInfo,
    compute_verdict,
    fetch_replication,
    lag_trend,
)


def _channel(**overrides: Any) -> ReplicaChannel:
    base: dict[str, Any] = {
        "channel": "",
        "io_running": "Yes",
        "sql_running": "Yes",
        "seconds_behind": 0,
        "source_host": "primary.example.com",
        "source_port": "3306",
        "source_log_file": "bin.000123",
        "read_source_log_pos": "456",
        "relay_source_log_file": "bin.000123",
        "exec_source_log_pos": "456",
        "relay_log_file": "relay.000045",
        "relay_log_pos": "789",
        "relay_log_space": 0,
        "retrieved_gtid_set": "",
        "executed_gtid_set": "",
        "auto_position": True,
        "parallel_workers": 0,
        "parallel_type": "",
        "busy_workers": 0,
        "last_io_error": "",
        "last_sql_error": "",
        "last_io_errno": "0",
        "last_sql_errno": "0",
    }
    base.update(overrides)
    return ReplicaChannel(**base)


# --- Verdict ---


def test_verdict_healthy_replica() -> None:
    info = ReplicationInfo(channels=[_channel(seconds_behind=0)])
    v = compute_verdict(info)
    assert v.level == "healthy"
    assert "HEALTHY" in v.text


def test_verdict_lagging_replica() -> None:
    info = ReplicationInfo(channels=[_channel(seconds_behind=120)])
    v = compute_verdict(info)
    assert v.level == "warn"
    assert "LAGGING" in v.text and "120s" in v.text


def test_verdict_broken_sql_thread() -> None:
    info = ReplicationInfo(
        channels=[_channel(sql_running="No", last_sql_error="duplicate key", last_sql_errno="1062")]
    )
    v = compute_verdict(info)
    assert v.level == "error"
    assert "BROKEN" in v.text and "1062" in v.text


def test_verdict_primary() -> None:
    info = ReplicationInfo(
        primary=PrimaryInfo(replicas=[ReplicaRow(server_id="2", host="r1", port="3306")])
    )
    v = compute_verdict(info)
    assert v.level == "info"
    assert "PRIMARY" in v.text and "1 replica" in v.text


def test_verdict_galera_synced() -> None:
    info = ReplicationInfo(
        cluster=ClusterInfo(enabled=True, local_state="Synced", cluster_size="3")
    )
    v = compute_verdict(info)
    assert v.level == "healthy"
    assert "GALERA" in v.text and "3 nodes" in v.text


def test_verdict_standalone() -> None:
    v = compute_verdict(ReplicationInfo())
    assert v.level == "info"
    assert "STANDALONE" in v.text


def test_broken_takes_priority_over_lag() -> None:
    """A broken thread outranks a lag warning."""
    info = ReplicationInfo(
        channels=[_channel(sql_running="No", seconds_behind=999, last_sql_error="boom")]
    )
    assert compute_verdict(info).level == "error"


# --- Lag trend ---


def test_lag_trend() -> None:
    assert lag_trend([]) == "—"
    assert lag_trend([5]) == "—"
    assert lag_trend([5, 10]) == "▲"
    assert lag_trend([10, 5]) == "▼"
    assert lag_trend([7, 7]) == "—"


# --- Fetch mapping (fake cursors) ---


class _FakeCursor:
    def __init__(self, script: dict[str, tuple[list[str], list[tuple[Any, ...]]]]) -> None:
        self._script = script
        self.description: list[Any] | None = None
        self._rows: list[tuple[Any, ...]] = []

    def execute(self, sql: str) -> None:
        # Match by keyword ignoring the /* mydba */ tag.
        for key, (cols, rows) in self._script.items():
            if key in sql:
                self.description = [(c,) for c in cols]
                self._rows = rows
                return
        self.description = None
        self._rows = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows

    def close(self) -> None:
        pass


class _FakeConnection:
    def __init__(self, script: dict[str, tuple[list[str], list[tuple[Any, ...]]]]) -> None:
        self._script = script

    def cursor(self, buffered: bool = False) -> _FakeCursor:
        return _FakeCursor(self._script)


def test_fetch_replica_channel() -> None:
    """A replica's SHOW REPLICA STATUS maps into a channel."""
    script = {
        "SHOW REPLICA STATUS": (
            [
                "Channel_Name",
                "Replica_IO_Running",
                "Replica_SQL_Running",
                "Seconds_Behind_Source",
                "Source_Host",
                "Source_Port",
                "Last_SQL_Error",
            ],
            [("", "Yes", "Yes", 5, "primary", "3306", "")],
        ),
    }
    info = fetch_replication(_FakeConnection(script))  # type: ignore[arg-type]
    assert info.is_replica
    ch = info.channels[0]
    assert ch.io_running == "Yes"
    assert ch.seconds_behind == 5
    assert ch.source_host == "primary"


def test_fetch_replica_relay_and_gtid() -> None:
    """Relay log details and GTID retrieved set map from SHOW REPLICA STATUS."""
    script = {
        "SHOW REPLICA STATUS": (
            [
                "Channel_Name",
                "Replica_IO_Running",
                "Replica_SQL_Running",
                "Seconds_Behind_Source",
                "Relay_Log_File",
                "Relay_Log_Pos",
                "Relay_Log_Space",
                "Retrieved_Gtid_Set",
            ],
            [("", "Yes", "Yes", 0, "relay.000007", "1024", 1048576, "uuid:1-100")],
        ),
    }
    info = fetch_replication(_FakeConnection(script))  # type: ignore[arg-type]
    ch = info.channels[0]
    assert ch.relay_log_file == "relay.000007"
    assert ch.relay_log_pos == "1024"
    assert ch.relay_log_space == 1048576
    assert ch.retrieved_gtid_set == "uuid:1-100"
    # The retrieved GTID set rolls up onto the shared GTID section.
    assert "uuid:1-100" in info.gtid.retrieved


def test_unapplied_bytes_same_file() -> None:
    """Unapplied bytes = read pos - exec pos when both are on the same file."""
    ch = _channel(
        source_log_file="bin.000010",
        read_source_log_pos="5000",
        relay_source_log_file="bin.000010",
        exec_source_log_pos="1200",
    )
    assert ch.unapplied_bytes == 3800


def test_unapplied_bytes_spans_files_is_none() -> None:
    """When the applier trails onto an earlier file the gap can't be derived."""
    ch = _channel(
        source_log_file="bin.000010",
        read_source_log_pos="5000",
        relay_source_log_file="bin.000009",
        exec_source_log_pos="900",
    )
    assert ch.unapplied_bytes is None


def test_non_galera_skips_status_query() -> None:
    """On a non-Galera server the wsrep_* status query is never issued.

    SHOW GLOBAL STATUS is only needed for cluster counters, so a plain server
    (no wsrep provider) must not pay for it.
    """
    executed: list[str] = []

    class _RecordingCursor:
        description: list[Any] | None = None

        def execute(self, sql: str) -> None:
            executed.append(sql)
            # Only answer the variables query; everything else is empty.
            if "SHOW GLOBAL VARIABLES" in sql:
                self.description = [("Variable_name",), ("Value",)]
                self._rows: list[tuple[Any, ...]] = [("gtid_mode", "OFF"), ("wsrep_on", "OFF")]
            else:
                self.description = None
                self._rows = []

        def fetchall(self) -> list[tuple[Any, ...]]:
            return self._rows

        def close(self) -> None:
            pass

    class _RecordingConnection:
        def cursor(self, buffered: bool = False) -> _RecordingCursor:
            return _RecordingCursor()

    fetch_replication(_RecordingConnection())  # type: ignore[arg-type]

    assert any("SHOW GLOBAL VARIABLES" in s for s in executed)
    assert not any("SHOW GLOBAL STATUS" in s for s in executed)


def test_global_variables_and_status_are_batched() -> None:
    """GTID and cluster values come from single batched var/status queries."""
    script = {
        "SHOW GLOBAL VARIABLES": (
            ["Variable_name", "Value"],
            [
                ("gtid_mode", "ON"),
                ("gtid_executed", "uuid:1-500"),
                ("gtid_purged", "uuid:1-100"),
                ("wsrep_provider", "/usr/lib/galera/libgalera.so"),
                ("wsrep_on", "ON"),
                ("wsrep_cluster_name", "my_cluster"),
            ],
        ),
        "SHOW GLOBAL STATUS": (
            ["Variable_name", "Value"],
            [
                ("wsrep_cluster_size", "3"),
                ("wsrep_cluster_status", "Primary"),
                ("wsrep_local_state_comment", "Synced"),
                ("wsrep_flow_control_paused", "0.001"),
            ],
        ),
    }
    info = fetch_replication(_FakeConnection(script))  # type: ignore[arg-type]

    assert info.gtid.enabled
    assert info.gtid.executed == "uuid:1-500"
    assert info.gtid.purged == "uuid:1-100"

    assert info.cluster.enabled
    assert info.cluster.cluster_name == "my_cluster"
    assert info.cluster.cluster_size == "3"
    assert info.cluster.cluster_status == "Primary"
    assert info.cluster.local_state == "Synced"
    assert info.cluster.flow_control_paused == "0.001"


def test_fetch_binlog_row_image_and_metadata() -> None:
    """binlog_row_image and binlog_row_metadata map into PrimaryInfo.

    All global variables are read in one batched query, so the fake returns
    several name/value rows for the single SHOW GLOBAL VARIABLES statement.
    """
    script = {
        "SHOW BINARY LOG STATUS": (["File", "Position"], [("bin.000010", 4)]),
        "SHOW GLOBAL VARIABLES": (
            ["Variable_name", "Value"],
            [
                ("binlog_row_image", "MINIMAL"),
                ("binlog_row_metadata", "FULL"),
            ],
        ),
    }
    info = fetch_replication(_FakeConnection(script))  # type: ignore[arg-type]
    assert info.primary.binlog_row_image == "MINIMAL"
    assert info.primary.binlog_row_metadata == "FULL"


def test_fetch_standalone_empty() -> None:
    """No replication anywhere yields empty sections."""
    info = fetch_replication(_FakeConnection({}))  # type: ignore[arg-type]
    assert not info.is_replica
    assert not info.primary.is_primary
    assert not info.cluster.enabled


def test_fetch_null_seconds_behind() -> None:
    """A NULL Seconds_Behind_Source maps to None (not replicating)."""
    script = {
        "SHOW REPLICA STATUS": (
            ["Channel_Name", "Replica_IO_Running", "Replica_SQL_Running", "Seconds_Behind_Source"],
            [("", "No", "No", None)],
        ),
    }
    info = fetch_replication(_FakeConnection(script))  # type: ignore[arg-type]
    assert info.channels[0].seconds_behind is None
