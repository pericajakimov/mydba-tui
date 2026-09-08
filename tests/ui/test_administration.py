"""Tests for the Administration Process List screen logic."""

from mydba_tui.services.processlist import ProcessRow
from mydba_tui.ui.screens.administration import AdministrationScreen


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


def test_bindings_present() -> None:
    """Screen exposes refresh, pause, filter, and kill bindings."""
    keys = [b.key for b in AdministrationScreen.BINDINGS]
    for key in ("r", "p", "s", "slash", "k", "shift+k", "escape"):
        assert key in keys, f"missing binding {key}"


def test_matches_by_user() -> None:
    """Filter matches on the user field, case-insensitively."""
    proc = _proc(user="reporting")
    assert AdministrationScreen._matches(proc, "report") is True
    assert AdministrationScreen._matches(proc, "REPORT") is True


def test_matches_by_query_text() -> None:
    """Filter matches within the query (Info) text."""
    proc = _proc(info="UPDATE inventory SET qty = 0")
    assert AdministrationScreen._matches(proc, "inventory") is True


def test_matches_no_hit() -> None:
    """Filter returns False when nothing contains the needle."""
    proc = _proc(user="app", info="SELECT 1")
    assert AdministrationScreen._matches(proc, "zzz") is False


def test_hide_sleeping_filter() -> None:
    """_visible_processes hides Sleep sessions when the toggle is on."""
    screen = AdministrationScreen()
    screen._processes = [
        _proc(id=1, command="Query"),
        _proc(id=2, command="Sleep"),
        _proc(id=3, command="Query"),
    ]
    screen._hide_sleeping = True
    visible = screen._visible_processes()
    assert {p.id for p in visible} == {1, 3}


def test_text_filter_applied() -> None:
    """_visible_processes applies the text filter across fields."""
    screen = AdministrationScreen()
    screen._processes = [
        _proc(id=1, user="app"),
        _proc(id=2, user="reporting"),
    ]
    screen._filter = "report"
    visible = screen._visible_processes()
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


def test_open_in_workspace_binding_present() -> None:
    """The 'w' binding opens the selected query in the SQL Workspace."""
    keys = [b.key for b in AdministrationScreen.BINDINGS]
    assert "w" in keys


def test_long_state_truncated_in_display_only() -> None:
    """A long State is truncated for the table cell but not in the row data."""
    from mydba_tui.ui.screens.administration import _STATE_TRUNCATE

    long_state = "Source has sent all binlog to replica; waiting for more updates"
    proc = _proc(state=long_state)

    screen = AdministrationScreen()
    cells = screen._row_cells(proc)
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
