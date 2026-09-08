"""Tests for the Administration Process List screen logic."""

from mydba_tui.services.processlist import ProcessRow
from mydba_tui.ui.screens.administration import (
    AdministrationScreen,
    ConnectionsView,
    LocksView,
    MetadataLocksView,
    ProcessListView,
    StatusView,
    TransactionsView,
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
    """The Process List view exposes refresh, pause, filter, and kill keys."""
    keys = _all_binding_keys(ProcessListView)
    for key in ("r", "p", "s", "slash", "k", "K", "w"):
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
    """The Connections view exposes refresh, pause, and filter keys."""
    keys = _all_binding_keys(ConnectionsView)
    for key in ("r", "p", "slash"):
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
    """The Transactions view exposes refresh, pause, filter, kill, workspace."""
    keys = _all_binding_keys(TransactionsView)
    for key in ("r", "p", "slash", "k", "w"):
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
    """The Locks view exposes refresh, pause, filter, and kill-blocker."""
    keys = _all_binding_keys(LocksView)
    for key in ("r", "p", "slash", "k"):
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
    """The Metadata Locks view exposes refresh, pause, filter, kill-blocker."""
    keys = _all_binding_keys(MetadataLocksView)
    for key in ("r", "p", "slash", "k"):
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
