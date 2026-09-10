"""Tests for the Administration Process List screen logic."""

from mydba_tui.services.processlist import ProcessRow
from mydba_tui.ui.screens.administration import (
    AdministrationScreen,
    ConnectionsView,
    LocksView,
    MetadataLocksView,
    PerformanceView,
    ProcessListView,
    ReplicationView,
    StatusView,
    TopQueriesView,
    TransactionsView,
    UsersView,
    VariablesView,
)


def _proc(**overrides: object) -> ProcessRow:
    base: dict[str, object] = {
        "id": 1,
        "user": "app",
        "host": "10.0.0.1",
        "db": "shop",
        "command": "Query",
        "time": 5,
        "state": "executing",
        "program": "mysql",
        "info": "SELECT * FROM orders",
    }
    base.update(overrides)
    return ProcessRow(**base)  # type: ignore[arg-type]


def test_screen_has_navigation_bindings() -> None:
    """The screen shell owns navigation (back, exit)."""
    keys = [b.key for b in AdministrationScreen.BINDINGS]
    assert "escape" in keys
    assert "f10" in keys


def _all_binding_keys(view_cls: type) -> set[str]:
    """Collect binding keys from a view class and its LiveTableView base."""
    from mydba_tui.ui.screens.administration import LiveTableView

    keys: set[str] = set()
    for cls in (view_cls, LiveTableView):
        keys.update(b.key for b in cls.BINDINGS)
    return keys


def test_process_list_view_bindings_present() -> None:
    """The Process List view exposes refresh, live, interval, filter, and kill."""
    keys = _all_binding_keys(ProcessListView)
    for key in ("r", "l", "i", "s", "slash", "k", "K", "w"):
        assert key in keys, f"missing binding {key}"


def test_matches_by_user() -> None:
    """Filter matches on the user field, case-insensitively."""
    view = ProcessListView()
    assert view._matches(_proc(user="reporting"), "report") is True
    assert view._matches(_proc(user="reporting"), "REPORT") is True


def test_matches_by_query_text() -> None:
    """Filter matches within the query (Info) text."""
    view = ProcessListView()
    assert view._matches(_proc(info="UPDATE inventory SET qty = 0"), "inventory") is True


def test_matches_no_hit() -> None:
    """Filter returns False when nothing contains the needle."""
    view = ProcessListView()
    assert view._matches(_proc(user="app", info="SELECT 1"), "zzz") is False


def test_hide_sleeping_filter() -> None:
    """_visible_items hides Sleep sessions when the toggle is on."""
    view = ProcessListView()
    view._items = [
        _proc(id=1, command="Query"),
        _proc(id=2, command="Sleep"),
        _proc(id=3, command="Query"),
    ]
    view._hide_sleeping = True
    visible = view._visible_items()
    assert {p.id for p in visible} == {1, 3}


def test_text_filter_applied() -> None:
    """_visible_items applies the text filter across fields."""
    view = ProcessListView()
    view._items = [
        _proc(id=1, user="app"),
        _proc(id=2, user="reporting"),
    ]
    view._filter = "report"
    visible = view._visible_items()
    assert [p.id for p in visible] == [2]


def test_workspace_snippet_includes_metadata_and_query() -> None:
    """The workspace snippet has the metadata header followed by the query."""
    from mydba_tui.ui.screens.administration import _build_workspace_snippet

    proc = _proc(
        id=23208297,
        user="perica",
        host="192.168.11.121",
        db="shop",
        command="Query",
        time=42,
        state="executing",
        info="SELECT * FROM orders WHERE id = 1",
    )
    snippet = _build_workspace_snippet(proc)

    assert snippet.startswith("-- SQL from PROCESSLIST")
    assert "-- Connection Id: 23208297" in snippet
    assert "-- User: perica" in snippet
    assert "-- Host: 192.168.11.121" in snippet
    assert "-- DB: shop" in snippet
    assert "-- Command: Query" in snippet
    assert "-- Time: 42 (42s)" in snippet
    assert "-- State: executing" in snippet
    assert snippet.rstrip().endswith("SELECT * FROM orders WHERE id = 1")


def test_workspace_snippet_empty_fields_render_as_none() -> None:
    """Empty DB/State render as 'None' to match MySQL client style."""
    from mydba_tui.ui.screens.administration import _build_workspace_snippet

    proc = _proc(db="", state="", info="SELECT 1")
    snippet = _build_workspace_snippet(proc)

    assert "-- DB: None" in snippet
    assert "-- State: None" in snippet


def test_long_state_truncated_in_display_only() -> None:
    """A long State is truncated for the table cell but not in the row data."""
    from mydba_tui.ui.screens.administration import _STATE_TRUNCATE

    long_state = "Source has sent all binlog to replica; waiting for more updates"
    proc = _proc(state=long_state)

    view = ProcessListView()
    cells = view._row_cells(proc)
    # State cell is index 6 (Id, User, Host, db, Command, Time, State, ...).
    state_cell = cells[6].plain
    assert state_cell.endswith("…")
    assert len(state_cell) == _STATE_TRUNCATE + 1

    # Underlying data keeps the full state for detail/filter/workspace use.
    assert proc.state == long_state


def test_format_seconds_human_readable() -> None:
    """Whole-second durations format into human-readable units."""
    from mydba_tui.ui.screens.administration import _format_seconds

    assert _format_seconds(42) == "42s"
    assert _format_seconds(95) == "1m 35s"
    assert _format_seconds(11760) == "3h 16m 0s"
    assert _format_seconds(90061) == "1d 1h 1m 1s"


def test_format_time_field_shows_raw_and_human() -> None:
    """The Time field shows raw seconds plus the human-readable form."""
    from mydba_tui.ui.screens.administration import _format_time_field

    assert _format_time_field(42) == "42 (42s)"
    assert _format_time_field(11760) == "11760 (3h 16m 0s)"


def test_workspace_snippet_time_is_human_readable() -> None:
    """The workspace snippet Time line includes the human-readable duration."""
    from mydba_tui.ui.screens.administration import _build_workspace_snippet

    proc = _proc(time=11760)
    snippet = _build_workspace_snippet(proc)
    assert "-- Time: 11760 (3h 16m 0s)" in snippet


def test_variables_view_bindings_present() -> None:
    """The Variables view exposes refresh and filter keys."""
    keys = [b.key for b in VariablesView.BINDINGS]
    assert "r" in keys
    assert "slash" in keys


def test_status_view_bindings_present() -> None:
    """The Status view exposes refresh and filter keys."""
    keys = [b.key for b in StatusView.BINDINGS]
    assert "r" in keys
    assert "slash" in keys


def test_keyvalue_filter_matches_name_and_value() -> None:
    """The key/value filter matches across both name and value."""
    view = VariablesView()
    view._rows = [
        ("max_connections", "151"),
        ("innodb_buffer_pool_size", "134217728"),
        ("version", "8.4.0"),
    ]

    view._filter = "buffer"
    assert [n for n, _ in view._visible_rows()] == ["innodb_buffer_pool_size"]

    # Match on value.
    view._filter = "8.4.0"
    assert [n for n, _ in view._visible_rows()] == ["version"]

    # No filter returns everything.
    view._filter = ""
    assert len(view._visible_rows()) == 3


def test_view_config_differs() -> None:
    """Variables and Status views declare distinct DOM prefixes and nouns."""
    assert VariablesView.id_prefix == "vars"
    assert StatusView.id_prefix == "status"
    assert VariablesView.noun == "variables"
    assert StatusView.noun == "status values"
    # Status reloads each visit; variables load once.
    assert VariablesView.load_once is True
    assert StatusView.load_once is False


def test_connections_view_bindings_present() -> None:
    """The Connections view exposes refresh, live, interval, and filter keys."""
    keys = _all_binding_keys(ConnectionsView)
    for key in ("r", "l", "i", "slash"):
        assert key in keys, f"missing binding {key}"


def test_connections_filter_matches_user_and_host() -> None:
    """The Connections filter matches across user and host."""
    from mydba_tui.services.connections import ConnectionStat

    view = ConnectionsView()
    view._items = [
        ConnectionStat(user="app", host="10.0.0.1", count=3),
        ConnectionStat(user="reporting", host="10.0.0.9", count=1),
    ]

    view._filter = "report"
    assert [s.user for s in view._visible_items()] == ["reporting"]

    # Match on host.
    view._filter = "0.0.1"
    assert [s.user for s in view._visible_items()] == ["app"]

    view._filter = ""
    assert len(view._visible_items()) == 2


def _trx(**overrides: object):
    from mydba_tui.services.transactions import TransactionRow

    base: dict[str, object] = {
        "trx_id": "421",
        "conn_id": 100,
        "user": "app",
        "host": "10.0.0.1",
        "db": "shop",
        "state": "RUNNING",
        "started": "2026-01-01 10:00:00",
        "age_seconds": 30,
        "rows_locked": 5,
        "query": "UPDATE orders SET status = 1",
    }
    base.update(overrides)
    return TransactionRow(**base)  # type: ignore[arg-type]


def test_transactions_view_bindings_present() -> None:
    """The Transactions view exposes refresh, live, filter, kill, workspace."""
    keys = _all_binding_keys(TransactionsView)
    for key in ("r", "l", "i", "slash", "k", "w"):
        assert key in keys, f"missing binding {key}"


def test_transactions_filter_matches_fields() -> None:
    """The Transactions filter matches user, host, state, and query."""
    view = TransactionsView()
    view._items = [
        _trx(trx_id="1", user="app", query="UPDATE orders SET x=1"),
        _trx(trx_id="2", user="reporting", query="SELECT * FROM sales"),
    ]

    view._filter = "report"
    assert [t.trx_id for t in view._visible_items()] == ["2"]  # type: ignore[attr-defined]

    view._filter = "orders"
    assert [t.trx_id for t in view._visible_items()] == ["1"]  # type: ignore[attr-defined]

    view._filter = ""
    assert len(view._visible_items()) == 2


def test_transaction_snippet_includes_metadata_and_query() -> None:
    """The transaction workspace snippet has a metadata header plus the query."""
    from mydba_tui.ui.screens.administration import _build_transaction_snippet

    trx = _trx(trx_id="777", conn_id=222, age_seconds=95, query="DELETE FROM t")
    snippet = _build_transaction_snippet(trx)
    assert snippet.startswith("-- SQL from transaction")
    assert "-- Trx ID: 777" in snippet
    assert "-- Connection Id: 222" in snippet
    assert "-- Age: 95 (1m 35s)" in snippet
    assert snippet.rstrip().endswith("DELETE FROM t")


def _lock(**overrides: object):
    from mydba_tui.services.locks import LockWait

    base: dict[str, object] = {
        "wait_age_secs": 12,
        "locked_schema": "shop",
        "locked_table": "orders",
        "locked_type": "RECORD",
        "waiting_pid": 101,
        "waiting_user": "app",
        "waiting_host": "10.0.0.1",
        "waiting_lock_mode": "X",
        "waiting_query": "UPDATE orders SET status = 1 WHERE id = 5",
        "blocking_pid": 202,
        "blocking_user": "reporting",
        "blocking_host": "10.0.0.2",
        "blocking_lock_mode": "X",
        "blocking_query": "SELECT * FROM orders FOR UPDATE",
    }
    base.update(overrides)
    return LockWait(**base)  # type: ignore[arg-type]


def test_locks_view_bindings_present() -> None:
    """The Locks view exposes refresh, live, filter, and kill-blocker."""
    keys = _all_binding_keys(LocksView)
    for key in ("r", "l", "i", "slash", "k"):
        assert key in keys, f"missing binding {key}"


def test_locks_filter_matches_users_table_query() -> None:
    """The Locks filter matches waiting/blocking users, table, and queries."""
    view = LocksView()
    view._items = [
        _lock(waiting_pid=1, blocking_user="reporting"),
        _lock(waiting_pid=2, blocking_user="etl", locked_table="invoices"),
    ]

    view._filter = "reporting"
    assert [lw.waiting_pid for lw in view._visible_items()] == [1]  # type: ignore[attr-defined]

    view._filter = "invoices"
    assert [lw.waiting_pid for lw in view._visible_items()] == [2]  # type: ignore[attr-defined]

    view._filter = ""
    assert len(view._visible_items()) == 2


def test_locks_row_key_pairs_waiting_and_blocking() -> None:
    """A lock wait's row key is the (waiting, blocking) pid pair."""
    view = LocksView()
    key = view._row_key(_lock(waiting_pid=101, blocking_pid=202))
    assert key == "101\x00202"


def _mdl(**overrides: object):
    from mydba_tui.services.metadata_locks import MetadataLockWait

    base: dict[str, object] = {
        "wait_age_secs": 20,
        "object_schema": "shop",
        "object_name": "orders",
        "waiting_pid": 101,
        "waiting_account": "app@10.0.0.1",
        "waiting_lock_type": "EXCLUSIVE",
        "waiting_query": "ALTER TABLE orders ADD COLUMN x INT",
        "blocking_pid": 202,
        "blocking_account": "reporting@10.0.0.2",
        "blocking_lock_type": "SHARED_READ",
    }
    base.update(overrides)
    return MetadataLockWait(**base)  # type: ignore[arg-type]


def test_metadata_locks_view_bindings_present() -> None:
    """The Metadata Locks view exposes refresh, live, filter, kill-blocker."""
    keys = _all_binding_keys(MetadataLocksView)
    for key in ("r", "l", "i", "slash", "k"):
        assert key in keys, f"missing binding {key}"


def test_metadata_locks_filter_matches_account_object_query() -> None:
    """The filter matches account, object, and query."""
    view = MetadataLocksView()
    view._items = [
        _mdl(waiting_pid=1, blocking_account="reporting@h"),
        _mdl(waiting_pid=2, object_name="invoices", blocking_account="etl@h"),
    ]

    view._filter = "reporting"
    assert [m.waiting_pid for m in view._visible_items()] == [1]  # type: ignore[attr-defined]

    view._filter = "invoices"
    assert [m.waiting_pid for m in view._visible_items()] == [2]  # type: ignore[attr-defined]

    view._filter = ""
    assert len(view._visible_items()) == 2


def test_metadata_locks_row_key_includes_object() -> None:
    """The row key combines waiting/blocking pids and the object."""
    view = MetadataLocksView()
    key = view._row_key(_mdl(waiting_pid=1, blocking_pid=2, object_schema="s", object_name="t"))
    assert key == "1\x002\x00s.t"


def _account(**overrides: object):
    from mydba_tui.services.users import UserAccount

    base: dict[str, object] = {
        "group": "Application Users",
        "group_color": "",
        "user": "app1_user",
        "host": "%",
        "locked": False,
        "password_expired": False,
        "password_last_changed": "2026-01-01 10:00:00",
        "plugin": "caching_sha2_password",
    }
    base.update(overrides)
    return UserAccount(**base)  # type: ignore[arg-type]


def test_live_views_start_with_live_off() -> None:
    """Live-capable views load once and never auto-start live updates."""
    for view_cls in (ProcessListView, ConnectionsView, TransactionsView):
        view = view_cls()
        assert view.supports_live is True
        assert view._live is False


def test_users_view_is_not_live() -> None:
    """The Users view has no live updates (load once, manual refresh only)."""
    assert UsersView.supports_live is False


def test_users_view_has_filter_and_refresh_bindings_only() -> None:
    """The Users view exposes filter and manual refresh, but no live/interval."""
    keys = _all_binding_keys(UsersView)
    assert "r" in keys
    assert "slash" in keys
    # No live-updates or interval keys on a manual-only tab.
    assert "l" not in keys
    assert "i" not in keys


def test_users_filter_matches_group_user_host_plugin() -> None:
    """The Users filter matches group, user, host, and plugin."""
    view = UsersView()
    view._items = [
        _account(user="app1_user", group="Application Users"),
        _account(user="john.doe", group="Personal Users", host="10.0.0.5"),
    ]

    view._filter = "personal"
    assert [a.user for a in view._visible_items()] == ["john.doe"]  # type: ignore[attr-defined]

    view._filter = "10.0.0.5"
    assert [a.user for a in view._visible_items()] == ["john.doe"]  # type: ignore[attr-defined]

    view._filter = ""
    assert len(view._visible_items()) == 2


def test_users_row_key_is_user_host() -> None:
    """A user's row key is the user@host pair."""
    view = UsersView()
    assert view._row_key(_account(user="app", host="%")) == "app\x00%"


def test_users_group_colors_respect_sql_then_auto() -> None:
    """SQL-provided colours are used; empty ones auto-assign distinctly."""
    view = UsersView()
    view._items = [
        _account(user="root", group="System Users", group_color="grey62"),
        _account(user="app", group="Application Users", group_color=""),
        _account(user="ro", group="Read-Only Users", group_color=""),
    ]
    colors = view._group_colors()
    # Explicit SQL colour honoured.
    assert colors["System Users"] == "grey62"
    # Auto-assigned groups get distinct palette colours.
    assert colors["Application Users"] != colors["Read-Only Users"]
    assert colors["Application Users"] in UsersView._GROUP_PALETTE
    assert colors["Read-Only Users"] in UsersView._GROUP_PALETTE


def test_replication_view_bindings_present() -> None:
    """The Replication view exposes refresh and live-toggle."""
    keys = [b.key for b in ReplicationView.BINDINGS]
    assert "r" in keys
    assert "l" in keys
    assert "i" in keys


def test_replication_view_lag_window_bounded() -> None:
    """The rolling lag window is capped at the interval-derived sample count."""
    from mydba_tui.services.replication import ReplicaChannel, ReplicationInfo

    view = ReplicationView()
    # Force a small window so the test is fast: 20s of history at 10s/sample = 2.
    view._LAG_WINDOW_SECONDS = 20
    view._interval = 10
    cap = view._lag_window
    assert cap == 2

    def channel(lag: int) -> ReplicaChannel:
        return ReplicaChannel(
            channel="",
            io_running="Yes",
            sql_running="Yes",
            seconds_behind=lag,
            source_host="h",
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

    for i in range(cap + 20):
        view._update_lag_samples(ReplicationInfo(channels=[channel(i)]))

    assert len(view._lag_samples) == cap
    # Keeps the most recent samples.
    assert view._lag_samples[-1] == cap + 19


def test_replication_lag_window_is_thirty_minutes_default() -> None:
    """The default window holds 30 minutes of samples for the given interval."""
    view = ReplicationView()
    assert view._LAG_WINDOW_SECONDS == 30 * 60
    view._interval = 3
    assert view._lag_window == (30 * 60) // 3  # 600 samples at 3s
    view._interval = 5
    assert view._lag_window == (30 * 60) // 5  # 360 samples at 5s


def test_replication_status_line_text() -> None:
    """The refresh-status text shows the live cadence, or an off hint."""
    view = ReplicationView()
    view._interval = 5

    view._live = True
    assert "every 5s" in view._status_markup()
    assert "live" in view._status_markup()

    view._live = False
    assert "off" in view._status_markup()
    assert "every 5s" not in view._status_markup()


def test_replication_toggle_live_flips_state() -> None:
    """Toggling live flips the flag; auto-refresh is off by default."""
    view = ReplicationView()
    # Stub out side effects that need a mounted app / DOM.
    view.notify = lambda *a, **k: None  # type: ignore[method-assign]
    view._render_status_line = lambda: None  # type: ignore[method-assign]
    view.action_refresh = lambda: None  # type: ignore[method-assign]

    assert view._live is False  # off by default
    view.action_toggle_live()
    assert view._live is True
    view.action_toggle_live()
    assert view._live is False


def test_render_lag_chart_flat_zero_still_renders() -> None:
    """A healthy replica (lag flat at 0) still renders a framed chart."""
    from mydba_tui.ui.screens.administration import _render_lag_chart

    chart = _render_lag_chart([0, 0, 0, 0, 0], width=60, height=6, interval=3)
    text = chart.plain
    # Not empty, has a y-axis (0s) and an x-axis frame + relative time labels.
    assert text.strip() != ""
    assert "0s" in text
    assert "└" in text
    assert "now" in text


def test_render_lag_chart_time_axis_scales_with_interval() -> None:
    """The x-axis span reflects sample count times the refresh interval."""
    from mydba_tui.ui.screens.administration import _render_lag_chart

    # 11 samples at 3s spacing -> 30s back.
    chart = _render_lag_chart([0] * 11, width=60, height=6, interval=3)
    assert "-30s" in chart.plain


def test_render_lag_chart_no_room_returns_empty() -> None:
    """Too little width yields an empty chart (nothing to draw)."""
    from mydba_tui.ui.screens.administration import _render_lag_chart

    assert _render_lag_chart([1, 2, 3], width=4, height=6, interval=3).plain == ""


def test_cycle_interval_advances_through_choices(monkeypatch: object) -> None:
    """Cycling steps through the fixed choices and wraps around, persisting."""
    import mydba_tui.config as config_mod
    from mydba_tui.config import Settings
    from mydba_tui.config.defaults import REFRESH_INTERVAL_CHOICES
    from mydba_tui.ui.screens.administration import _current_interval, _cycle_interval

    saved: list[int] = []
    monkeypatch.setattr(  # type: ignore[attr-defined]
        config_mod, "save_settings", lambda s: saved.append(s.refresh_interval)
    )

    class _App:
        def __init__(self) -> None:
            self.settings = Settings(refresh_interval=REFRESH_INTERVAL_CHOICES[0])

    app = _App()
    assert _current_interval(app) == REFRESH_INTERVAL_CHOICES[0]

    # Walk the whole ring and confirm we return to the start.
    seen = [_cycle_interval(app) for _ in REFRESH_INTERVAL_CHOICES]
    assert seen == [*REFRESH_INTERVAL_CHOICES[1:], REFRESH_INTERVAL_CHOICES[0]]
    # Each step was persisted.
    assert saved == seen


def test_cycle_interval_snaps_unknown_value_to_first_choice(monkeypatch: object) -> None:
    """A non-standard stored interval snaps to the first choice on cycle."""
    import mydba_tui.config as config_mod
    from mydba_tui.config import Settings
    from mydba_tui.config.defaults import REFRESH_INTERVAL_CHOICES
    from mydba_tui.ui.screens.administration import _cycle_interval

    monkeypatch.setattr(config_mod, "save_settings", lambda s: None)  # type: ignore[attr-defined]

    class _App:
        def __init__(self) -> None:
            self.settings = Settings(refresh_interval=7)  # not a choice

    assert _cycle_interval(_App()) == REFRESH_INTERVAL_CHOICES[0]


def test_top_queries_view_bindings_present() -> None:
    """Top Queries exposes refresh, live, interval, filter, and workspace."""
    from mydba_tui.ui.screens.administration import LiveTableView

    keys: set[str] = set()
    for cls in (TopQueriesView, LiveTableView):
        keys.update(b.key for b in cls.BINDINGS)
    for key in ("r", "l", "i", "slash", "w"):
        assert key in keys, f"missing binding {key}"


def test_perf_grid_row_helpers() -> None:
    """A perf grid maps rows to dicts, keys, and filters by any cell."""
    from mydba_tui.services.performance import GridData

    view = TopQueriesView()
    view._grid = GridData(
        columns=["query", "db", "digest"],
        rows=[["SELECT 1", "shop", "abc"], ["UPDATE t", "app", "def"]],
    )

    # Row -> dict by header.
    assert view._row_dict(["SELECT 1", "shop", "abc"]) == {
        "query": "SELECT 1",
        "db": "shop",
        "digest": "abc",
    }
    # Row key is stable and derived from contents.
    assert view._row_key(["SELECT 1", "shop", "abc"]) == "SELECT 1\x00shop\x00abc"
    # Filter matches across all cells.
    assert view._matches(["SELECT 1", "shop", "abc"], "shop") is True
    assert view._matches(["SELECT 1", "shop", "abc"], "nope") is False


def test_perf_grid_starts_with_live_off() -> None:
    """Perf grids load once and never auto-start live updates."""
    view = TopQueriesView()
    assert view.supports_live is True
    assert view._live is False


def test_performance_view_refresh_data_is_safe_without_dom() -> None:
    """PerformanceView.refresh_data is defensive when not mounted (no crash)."""
    # Not mounted → query_one raises internally and is swallowed; no exception.
    view = PerformanceView()
    view.refresh_data()


def test_users_perf_view_breakdowns_are_wired() -> None:
    """The Users perf view declares the five keyed breakdown views."""
    from mydba_tui.ui.screens.administration import UsersPerfView

    labels = [b.label for b in UsersPerfView._BREAKDOWNS]
    assert labels == [
        "Statement Latency",
        "Statement Types",
        "Stages",
        "File I/O",
        "File I/O Types",
    ]
    # Every breakdown points at a real .sql file under sql/admin/perf/.
    from mydba_tui.services.sql_loader import load_sql

    for spec in UsersPerfView._BREAKDOWNS:
        sql = load_sql(spec.sql_file)
        assert "%s" in sql  # keyed/parameterized
        assert "/* mydba */" in sql  # tagged


def test_hosts_perf_view_breakdowns_are_wired() -> None:
    """The Hosts perf view declares five host-keyed breakdown views."""
    from mydba_tui.services.sql_loader import load_sql
    from mydba_tui.ui.screens.administration import HostsPerfView

    labels = [b.label for b in HostsPerfView._BREAKDOWNS]
    assert labels == [
        "Statement Latency",
        "Statement Types",
        "Stages",
        "File I/O",
        "File I/O Types",
    ]
    for spec in HostsPerfView._BREAKDOWNS:
        sql = load_sql(spec.sql_file)
        assert "%s" in sql
        assert "host" in sql.lower()


def test_all_perf_views_start_live_off_and_load_grids() -> None:
    """Every Performance sub-tab view is live-off by default and points at SQL."""
    from mydba_tui.services.sql_loader import load_sql
    from mydba_tui.ui.screens.administration import (
        FullScansView,
        HostsPerfView,
        IndexesPerfView,
        IoPerfView,
        MemoryPerfView,
        TablesPerfView,
        UsersPerfView,
        WaitsPerfView,
    )

    views = [
        TopQueriesView,
        UsersPerfView,
        HostsPerfView,
        WaitsPerfView,
        IoPerfView,
        TablesPerfView,
        IndexesPerfView,
        FullScansView,
        MemoryPerfView,
    ]
    for cls in views:
        view = cls()
        assert view.supports_live is True
        assert view._live is False

    # Every breakdown spec across the families points at a loadable, tagged file.
    for cls in views:
        for spec in getattr(cls, "_BREAKDOWNS", []):
            sql = load_sql(spec.sql_file)
            assert "/* mydba */" in sql
            # Keyed breakdowns must be parameterized; global-context ones must not.
            assert ("%s" in sql) == spec.keyed


def test_render_grid_table_states() -> None:
    """The breakdown table renderer handles available/empty/unavailable."""
    from mydba_tui.services.performance import GridData
    from mydba_tui.ui.screens.administration import _render_grid_table

    # Unavailable and empty both render a note (a Static), not a crash.
    assert _render_grid_table(GridData([], [], available=False)) is not None
    assert _render_grid_table(GridData(["a"], [], available=True)) is not None
    # With data, it renders a table Static.
    assert _render_grid_table(GridData(["a", "b"], [["1", "2"]], available=True)) is not None
