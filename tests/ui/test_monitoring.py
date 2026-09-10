"""Tests for the Monitoring screen logic (formatters, specs, live model)."""

from mydba_tui.services.monitoring import Snapshot
from mydba_tui.ui.screens.monitoring import (
    OverviewView,
    _fmt_bytes,
    _fmt_conns,
    _fmt_num,
    _fmt_uptime,
)


def test_fmt_num_compact() -> None:
    assert _fmt_num(5) == "5.0"
    assert _fmt_num(150) == "150"
    assert _fmt_num(1500) == "1.5k"
    assert _fmt_num(2_500_000) == "2.5M"


def test_fmt_bytes_human() -> None:
    assert _fmt_bytes(512) == "512 B"
    assert _fmt_bytes(2048) == "2.0 KiB"
    assert _fmt_bytes(5 * 1024 * 1024) == "5.0 MiB"


def test_fmt_uptime() -> None:
    assert _fmt_uptime(90) == "1m"
    assert _fmt_uptime(3 * 3600 + 12 * 60) == "3h 12m"
    assert _fmt_uptime(12 * 86400 + 4 * 3600) == "12d 04h"


def test_fmt_conns_uses_connected_and_max() -> None:
    snap = Snapshot(status={"threads_connected": 8.0}, variables={"max_connections": "512"})
    assert _fmt_conns(snap) == "8 / 512"


def test_locks_view_graphs() -> None:
    """The Locks sub-tab defines its lock-contention graphs."""
    from mydba_tui.ui.screens.monitoring import LocksView

    view = LocksView()
    keys = [g.key for g in view.graphs]
    assert keys == [
        "row_lock_waits",
        "row_lock_time_avg",
        "table_locks_waited",
        "row_lock_current",
    ]


def test_replication_mon_view_body_and_no_replica_note() -> None:
    """The Replication sub-tab builds a per-channel body; empty when standalone."""
    from mydba_tui.services.replication import ReplicaChannel, ReplicationInfo
    from mydba_tui.ui.screens.monitoring import ReplicationMonView

    view = ReplicationMonView()
    # A replica channel renders a status body mentioning the source.
    ch = ReplicaChannel(
        channel="",
        io_running="Yes",
        sql_running="Yes",
        seconds_behind=3,
        source_host="primary",
        source_port="3306",
        source_log_file="b",
        read_source_log_pos="1",
        relay_source_log_file="b",
        exec_source_log_pos="1",
        relay_log_file="r",
        relay_log_pos="1",
        relay_log_space=0,
        retrieved_gtid_set="",
        executed_gtid_set="",
        auto_position=True,
        parallel_workers=0,
        parallel_type="",
        busy_workers=0,
        last_io_error="",
        last_sql_error="",
        last_io_errno="0",
        last_sql_errno="0",
    )
    body = view._build_body(ReplicationInfo(channels=[ch]))
    assert "Replica" in body
    assert "primary:3306" in body


def test_set_context_updates_interval_and_sample_cap() -> None:
    """The screen pushes interval/live into a sub-view via set_context."""
    view = OverviewView()
    view.set_context(interval=10, live=False)
    assert view._interval == 10
    assert view._live is False
    # Sample cap = window / interval (30 min at 10s = 180 samples).
    assert view._sample_cap == (30 * 60) // 10


def test_monitoring_screen_owns_live_interval_bindings() -> None:
    """The Monitoring screen exposes the R/L/I controls (moved off sub-views)."""
    from mydba_tui.ui.screens.monitoring import MonitoringScreen

    keys = [b.key for b in MonitoringScreen.BINDINGS]
    assert "r" in keys
    assert "l" in keys
    assert "i" in keys
    # Sub-views no longer carry their own control bindings.
    assert list(OverviewView.BINDINGS) == []


def test_overview_starts_live_and_defines_graphs_and_metrics() -> None:
    """Overview is live-by-default with the documented four graphs."""
    view = OverviewView()
    assert view._live is True  # dashboards start live
    keys = [g.key for g in view.graphs]
    assert keys == ["qps", "conns", "rows_read", "rows_written"]
    assert len(view.metrics) >= 3


def test_buffer_pool_hit_rate() -> None:
    """Hit rate = 100 * (1 - disk_reads/logical_requests) over the interval."""
    from mydba_tui.ui.screens.monitoring import _buffer_pool_hit_rate

    prev = Snapshot(
        status={"innodb_buffer_pool_read_requests": 0.0, "innodb_buffer_pool_reads": 0.0}
    )
    cur = Snapshot(
        status={"innodb_buffer_pool_read_requests": 1000.0, "innodb_buffer_pool_reads": 10.0}
    )
    assert _buffer_pool_hit_rate(prev, cur) == 99.0
    # No logical reads in the interval → treated as 100% (nothing to miss).
    flat = Snapshot(status={"innodb_buffer_pool_read_requests": 1000.0})
    assert _buffer_pool_hit_rate(cur, flat) == 100.0


def test_pct_dirty_and_history_list() -> None:
    """Dirty-page percentage and history list length format correctly."""
    from mydba_tui.ui.screens.monitoring import _history_list, _pct_dirty

    s = Snapshot(
        status={
            "innodb_buffer_pool_pages_total": 1000.0,
            "innodb_buffer_pool_pages_dirty": 125.0,
        },
        history_list_length=4200,
    )
    assert _pct_dirty(s) == "12.5%"
    assert _history_list(s) == "4200"
    # Unknown history list length shows a dash.
    assert _history_list(Snapshot(history_list_length=-1)) == "—"


def test_innodb_view_graphs_and_metrics() -> None:
    """The InnoDB sub-tab defines its four graphs and metrics strip."""
    from mydba_tui.ui.screens.monitoring import InnoDBView

    view = InnoDBView()
    assert view._live is True
    keys = [g.key for g in view.graphs]
    assert keys == ["hit_rate", "flushed", "rows_rw", "row_lock_waits"]
    assert [m.label for m in view.metrics] == [
        "Buffer pool",
        "Dirty pages",
        "History list",
        "Log waits",
    ]


def test_throughput_view_graphs_and_connection_errors() -> None:
    """Throughput sub-tab graphs plus the connection-errors sum metric."""
    from mydba_tui.ui.screens.monitoring import ThroughputView, _connection_errors

    view = ThroughputView()
    keys = [g.key for g in view.graphs]
    assert keys == ["selects", "writes", "net_in", "net_out"]

    s = Snapshot(
        status={
            "connection_errors_max_connections": 3.0,
            "connection_errors_internal": 2.0,
            "queries": 100.0,  # unrelated, must not be counted
        }
    )
    assert _connection_errors(s) == "5"


def test_overview_graph_value_callables_compute_rates() -> None:
    """The graph specs compute sensible values from two snapshots."""
    view = OverviewView()
    prev = Snapshot(
        status={"queries": 0.0, "innodb_rows_read": 0.0, "threads_connected": 4.0},
        taken_at=0.0,
    )
    cur = Snapshot(
        status={"queries": 100.0, "innodb_rows_read": 50.0, "threads_connected": 6.0},
        taken_at=10.0,
    )
    by_key = {g.key: g for g in view.graphs}
    assert by_key["qps"].value(prev, cur) == 10.0  # 100/10
    assert by_key["rows_read"].value(prev, cur) == 5.0  # 50/10
    # A gauge graph reports the current absolute value, not a rate.
    assert by_key["conns"].value(prev, cur) == 6.0
