"""
Administration screen.

Provides operational visibility for day-to-day administration. The first
section is the Process List: a live, filterable view of active MySQL sessions
with the ability to terminate a session or its running query.

All SQL executed here is written to the SQL log for transparency.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.markup import escape as rich_escape
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.timer import Timer
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Static,
    TabbedContent,
    TabPane,
)

from mydba_tui.config.defaults import DEFAULT_REFRESH_INTERVAL, REFRESH_INTERVAL_CHOICES
from mydba_tui.services.connections import ConnectionStat, fetch_connection_stats
from mydba_tui.services.locks import LOCK_COLUMNS, LockWait, fetch_lock_waits
from mydba_tui.services.metadata_locks import (
    MDL_COLUMNS,
    MetadataLockWait,
    fetch_metadata_lock_waits,
)
from mydba_tui.services.performance import (
    GridData,
    StatementDigestSample,
    fetch_breakdown,
    fetch_statement_digest_sample,
    fetch_view,
)
from mydba_tui.services.processlist import (
    PROCESS_COLUMNS,
    ProcessRow,
    fetch_processes,
    kill_session,
)
from mydba_tui.services.replication import (
    ReplicationInfo,
    compute_verdict,
    fetch_replication,
    lag_trend,
)
from mydba_tui.services.status import fetch_status
from mydba_tui.services.transactions import (
    TRANSACTION_COLUMNS,
    StatementHistoryEntry,
    TransactionRow,
    fetch_statement_history,
    fetch_transactions,
)
from mydba_tui.services.users import USER_COLUMNS, UserAccount, fetch_users
from mydba_tui.services.variables import fetch_variables
from mydba_tui.ui.screens.workspace import WorkspaceScreen
from mydba_tui.ui.widgets import ConfirmDialog, StatusBar


def _current_interval(app: object) -> int:
    """The active auto-refresh interval (seconds) from app settings."""
    value = getattr(getattr(app, "settings", None), "refresh_interval", DEFAULT_REFRESH_INTERVAL)
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return DEFAULT_REFRESH_INTERVAL


def _cycle_interval(app: object) -> int:
    """Advance the app's auto-refresh interval to the next fixed choice.

    Cycles through REFRESH_INTERVAL_CHOICES (wrapping around), persists the new
    value to settings, and returns it. Shared by every auto-refreshing view so
    changing the interval on one tab applies everywhere.
    """
    from mydba_tui.config import save_settings

    settings = getattr(app, "settings", None)
    current = _current_interval(app)
    choices = REFRESH_INTERVAL_CHOICES
    try:
        nxt = choices[(choices.index(current) + 1) % len(choices)]
    except ValueError:
        # Current value isn't one of the choices — snap to the first.
        nxt = choices[0]
    if settings is not None:
        settings.refresh_interval = nxt
        try:
            save_settings(settings)
        except Exception:
            pass
    return nxt


# Maximum characters of the Info (query) column shown inline in the table.
_INFO_TRUNCATE = 80

# Maximum characters of the State column shown inline (some replication states
# are very long, e.g. "Source has sent all binlog to replica; ...").
_STATE_TRUNCATE = 30


def _meta_value(val: object) -> str:
    """Format a metadata value for the comment header.

    Empty/None values render as "None" to mirror the MySQL client / Workbench
    style (e.g. an unset DB or State shows as "None").
    """
    s = "" if val is None else str(val)
    return s if s.strip() else "None"


def _explain_mode(mode: str) -> str:
    """Format a lock mode/type as 'CODE (Explanation)' for the detail view."""
    from mydba_tui.renderers.table import explain_lock_mode

    code = (mode or "").strip()
    if not code:
        return "None"
    explanation = explain_lock_mode(code)
    return f"{code} ({explanation})" if explanation and explanation != code else code


def _format_seconds(seconds: int) -> str:
    """Format a whole-second duration in human-readable form.

    Examples: 42 -> "42s", 95 -> "1m 35s", 11760 -> "3h 16m 0s".
    """
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, mins = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {mins}m {secs}s"
    days, hrs = divmod(hours, 24)
    return f"{days}d {hrs}h {mins}m {secs}s"


def _format_time_field(seconds: int) -> str:
    """Render the Time field as raw seconds plus a human-readable form."""
    return f"{seconds} ({_format_seconds(seconds)})"


def _format_bytes(num: int) -> str:
    """Format a byte count in human-readable units."""
    size = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _render_lag_chart(
    samples: list[int], width: int, height: int, interval: int, window_seconds: int = 30 * 60
) -> Text:
    """Render the replica-lag chart over a fixed time window.

    The x-axis is a fixed window (default 30 min); the newest sample sits at the
    right edge and the line fills from the right toward the left as history
    builds. A flat/zero series still reads as a clear baseline (a 5s y-axis
    floor keeps the frame from collapsing). Uses the shared framed renderer so
    the Monitoring graphs and this one look and behave identically.

    Args:
        samples: Lag values (seconds), oldest first.
        width: Available width in cells.
        height: Chart height in cells.
        interval: Seconds between samples (the refresh interval).
        window_seconds: Fixed x-axis span in seconds.

    Returns:
        A Rich Text chart (empty Text only if there is truly no room).
    """
    from mydba_tui.renderers.chart import render_timeseries

    if not samples:
        return Text()
    peak = max(samples)
    return render_timeseries(
        [float(s) for s in samples],
        width,
        height,
        interval,
        window_seconds,
        unit="s",
        color="cyan",
        # Floor the ceiling so a healthy (flat 0) replica reads as a baseline.
        y_max=float(max(peak, 5)),
        value_fmt=lambda v: f"{int(v)}",
    )


def _render_statement_history(history: list[StatementHistoryEntry] | None) -> Static:
    """Render statement history as an aligned table inside a Static widget.

    Used by the detail modals (Transactions, InnoDB Locks, Metadata Locks) so
    a session's recent statements are shown consistently. A Rich table is used
    (rather than a DataTable widget) so it can be built directly in compose.

    Args:
        history: The statements (most recent first), an empty list, or None
            when statement history is unavailable/not connected.

    Returns:
        A Static widget containing the rendered history or an explanatory note.
    """
    from rich.table import Table

    from mydba_tui.ui.mysql_highlight import highlight_mysql

    if history is None:
        return Static(
            "[dim]Unavailable — requires performance_schema statement history.[/dim]",
            classes="detail-sql",
        )
    if not history:
        return Static("[dim]No recent statements.[/dim]", classes="detail-sql")

    table: Table = Table(expand=True, show_edge=False, pad_edge=False)
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Duration", justify="right", style="dim", no_wrap=True)
    table.add_column("Statement", ratio=1)
    for i, entry in enumerate(history, 1):
        duration = f"{entry.duration_ms:.1f} ms" if entry.duration_ms else "—"
        table.add_row(str(i), duration, highlight_mysql(entry.sql))
    return Static(table, classes="detail-sql")


def _view_is_active_tab(widget: object) -> bool:
    """Return True if the widget's enclosing TabPane is the active tab.

    Used by live views to skip background auto-refresh (and its DB query) when
    their tab is not visible. Defaults to True if the structure can't be
    resolved, so a view never silently stops refreshing.
    """
    from textual.widget import Widget
    from textual.widgets import TabbedContent, TabPane

    if not isinstance(widget, Widget):
        return True
    pane: TabPane | None = None
    node: Widget | None = widget
    while node is not None:
        if isinstance(node, TabPane):
            pane = node
            break
        parent = node.parent
        node = parent if isinstance(parent, Widget) else None
    if pane is None:
        return True
    tabbed = pane.parent
    while tabbed is not None and not isinstance(tabbed, TabbedContent):
        tabbed = tabbed.parent
    if not isinstance(tabbed, TabbedContent):
        return True
    return tabbed.active == pane.id


def _build_workspace_snippet(proc: ProcessRow) -> str:
    """Build the SQL snippet (metadata comment header + query) for the workspace."""
    query = (proc.info or "").strip()
    lines = [
        "-- SQL from PROCESSLIST",
        f"-- Connection Id: {proc.id}",
        f"-- User: {_meta_value(proc.user)}",
        f"-- Host: {_meta_value(proc.host)}",
        f"-- DB: {_meta_value(proc.db)}",
        f"-- Command: {_meta_value(proc.command)}",
        f"-- Time: {_format_time_field(proc.time)}",
        f"-- State: {_meta_value(proc.state)}",
        f"-- Program: {_meta_value(proc.program)}",
        "",
        query,
    ]
    return "\n".join(lines)


def _build_transaction_snippet(trx: TransactionRow) -> str:
    """Build the SQL snippet (metadata comment header + query) for a transaction."""
    query = (trx.query or "").strip()
    lines = [
        "-- SQL from transaction",
        f"-- Trx ID: {trx.trx_id}",
        f"-- Connection Id: {trx.conn_id}",
        f"-- User: {_meta_value(trx.user)}",
        f"-- Host: {_meta_value(trx.host)}",
        f"-- DB: {_meta_value(trx.db)}",
        f"-- State: {_meta_value(trx.state)}",
        f"-- Started: {_meta_value(trx.started)}",
        f"-- Age: {_format_time_field(trx.age_seconds)}",
        f"-- Rows locked: {trx.rows_locked}",
        "",
        query,
    ]
    return "\n".join(lines)


class LiveTableView(Vertical):
    """Base for a live, auto-refreshing, filterable multi-column table view.

    Provides the shared machinery for the Process List, Connections, and
    Transactions sections: an auto-refresh timer gated on the active tab, a
    pausable refresh (``p``) with manual refresh (``r``), a client-side text
    filter (``/`` with Esc to clear), cursor preservation across refreshes, and
    an info line with paused/filter flags.

    Subclasses configure the DOM id prefix, column headers, filter placeholder,
    and noun, and implement the data hooks: ``_fetch``, ``_row_key``,
    ``_row_cells``, and ``_matches``.
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh", key_display="R", priority=True),
        Binding("slash", "filter", "Filter", key_display="/"),
    ]

    # Live-update bindings, added by subclasses that support live refresh (all
    # except Users). Kept out of the base BINDINGS so manual-only tabs don't
    # surface L/I in the footer (Textual merges bindings up the MRO).
    LIVE_BINDINGS = [
        Binding("l", "toggle_live", "Live On/Off", key_display="L"),
        Binding("i", "cycle_interval", "Interval", key_display="I"),
    ]

    DEFAULT_CSS = """
    LiveTableView {
        height: 1fr;
    }

    LiveTableView .live-info {
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }

    LiveTableView .live-table {
        height: 1fr;
    }

    LiveTableView .live-filter {
        display: none;
        height: auto;
        border: tall $accent;
    }

    LiveTableView .live-filter.visible {
        display: block;
    }
    """

    # --- Subclass configuration (override) ---
    id_prefix: str = "live"
    columns: tuple[str, ...] = ()
    filter_placeholder: str = "Filter — Enter to keep, Esc to clear"
    noun: str = "rows"
    # When True, the view offers opt-in live updates (L toggles them; I cycles
    # the interval). Live updates are always OFF until the user turns them on —
    # the view loads its data once on open and otherwise refreshes only on R.
    # When False the view has no live option at all (e.g. Users).
    supports_live: bool = True

    # --- Data hooks (subclasses implement) ---
    def _fetch(self) -> list[object]:
        """Return the current list of row items. Subclasses override."""
        raise NotImplementedError

    def _row_key(self, item: object) -> str:
        """Return a stable string key for an item (for cursor preservation)."""
        raise NotImplementedError

    def _row_cells(self, item: object) -> list[Text]:
        """Return the styled cells for an item, in column order."""
        raise NotImplementedError

    def _matches(self, item: object, needle: str) -> bool:
        """Return True if the item matches the (lowercased) filter needle."""
        raise NotImplementedError

    def _extra_flags(self) -> list[str]:
        """Optional extra info-line flags (e.g. a hide-sleeping toggle)."""
        return []

    def _pre_filter(self, items: list[object]) -> list[object]:
        """Optional non-text filtering applied before the text filter."""
        return items

    def __init__(self) -> None:
        """Initialize live view state."""
        super().__init__()
        self._items: list[object] = []
        # Live updates are opt-in and start OFF; the view loads once on open.
        self._live: bool = False
        self._filter: str = ""
        self._refresh_timer: Timer | None = None

    # --- DOM helpers ---

    @property
    def _info_id(self) -> str:
        return f"{self.id_prefix}-info"

    @property
    def _table_id(self) -> str:
        return f"{self.id_prefix}-table"

    @property
    def _filter_id(self) -> str:
        return f"{self.id_prefix}-filter"

    def compose(self) -> ComposeResult:
        """Build the live table layout."""
        yield Static("", id=self._info_id, classes="live-info")
        table: DataTable[Text] = DataTable(
            id=self._table_id, classes="live-table", zebra_stripes=True
        )
        table.cursor_type = "row"
        yield table
        yield Input(placeholder=self.filter_placeholder, id=self._filter_id, classes="live-filter")

    def on_mount(self) -> None:
        """Set up the table columns and load the data once.

        Live updates are opt-in (L) and off by default, so we do not query on a
        timer here — the tab simply loads its data once. The refresh timer is
        created only when the user enables live updates.
        """
        table = self.query_one(f"#{self._table_id}", DataTable)
        for col in self.columns:
            table.add_column(col, key=col)

        # First load is deferred so the tab paints (with a "Loading…" note)
        # before the query runs — on a busy server the query can take a moment.
        self._load_deferred()

    def _start_timer(self) -> None:
        """(Re)start the live-update timer at the current interval."""
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
        self._refresh_timer = self.set_interval(_current_interval(self.app), self._on_refresh_tick)

    def refresh_data(self) -> None:
        """Public hook to reload data (called when the tab is shown).

        Re-entering a tab is instant: if data is already loaded we keep it (a
        fresh query would be wasteful and could stutter a busy server). Only
        the first activation loads.
        """
        if self._items:
            return
        self._load_deferred()

    def _load_deferred(self) -> None:
        """Paint a loading note, then run the query on the next tick.

        Keeps the DB query on the UI thread (the shared connection is not
        thread-safe) while letting the tab paint first, so switching to a tab
        never looks frozen while the first query runs.
        """
        if not self._items:
            self._show_message("[cyan]⟳ Loading…[/cyan]")
            # Short timer so the loading note paints before the query blocks.
            self.set_timer(0.05, self.action_refresh)
        else:
            self.call_after_refresh(self.action_refresh)

    # --- Data loading ---

    def _on_refresh_tick(self) -> None:
        """Timer callback — fetch only while live AND this tab is active.

        Background tabs must not query the shared connection; that both wastes
        the connection and slows the visible tab.
        """
        if not self._live or not _view_is_active_tab(self):
            return
        self.action_refresh()

    def action_refresh(self) -> None:
        """Reload data (synchronous, single-threaded connection).

        The shared MySQL connection is used single-threaded throughout the app
        (the object browser queries it the same way), and mysql-connector
        connections are not thread-safe, so these queries run on the UI thread.
        """
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self._show_message("[yellow]Not connected to a database.[/yellow]")
            return

        try:
            items = self._fetch()
        except Exception as e:
            self._show_message(f"[red]Error: {e}[/red]")
            return

        self._render_table(items)

    def _show_message(self, markup: str) -> None:
        """Show a message in the info line."""
        self.query_one(f"#{self._info_id}", Static).update(markup)

    def _render_table(self, items: list[object]) -> None:
        """Populate the table, preserving cursor position by row key."""
        self._items = items
        table = self.query_one(f"#{self._table_id}", DataTable)
        selected_key = self._selected_key()

        table.clear()
        visible = self._visible_items()
        restore_row = 0
        for row_idx, item in enumerate(visible):
            key = self._row_key(item)
            table.add_row(*self._row_cells(item), key=key)
            if key == selected_key:
                restore_row = row_idx

        if visible:
            try:
                table.move_cursor(row=restore_row)
            except Exception:
                pass

        self._update_info(len(visible), len(items))

    def _visible_items(self) -> list[object]:
        """Apply subclass pre-filter and the text filter."""
        result = self._pre_filter(self._items)
        if self._filter:
            needle = self._filter.lower()
            result = [it for it in result if self._matches(it, needle)]
        return result

    def _update_info(self, shown: int, total: int) -> None:
        """Update the info line above the table."""
        flags = []
        if self.supports_live:
            if self._live:
                flags.append(f"[green]● live[/green] every {_current_interval(self.app)}s")
            else:
                flags.append("[dim]○ live off[/dim]")
        flags.extend(self._extra_flags())
        if self._filter:
            flags.append(f"filter: '{self._filter}'")
        suffix = f"  ({', '.join(flags)})" if flags else ""
        self._show_message(f"[bold]{shown}[/bold] of {total} {self.noun}{suffix}")

    # --- Selection ---

    def _selected_key(self) -> str | None:
        """Return the row key of the selected row, if any."""
        table = self.query_one(f"#{self._table_id}", DataTable)
        if table.row_count == 0:
            return None
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        except Exception:
            return None
        return None if row_key.value is None else str(row_key.value)

    def _selected_item(self) -> object | None:
        """Return the item for the selected row, if any."""
        key = self._selected_key()
        if key is None:
            return None
        return next((it for it in self._items if self._row_key(it) == key), None)

    # --- View controls ---

    def action_toggle_live(self) -> None:
        """Turn live auto-refresh on or off (no-op for non-live views)."""
        if not self.supports_live:
            return
        self._live = not self._live
        if self._live:
            self._start_timer()
            self.action_refresh()  # refresh at once so the data is current
            self.notify(f"Live updates on — every {_current_interval(self.app)}s.")
        else:
            if self._refresh_timer is not None:
                self._refresh_timer.stop()
                self._refresh_timer = None
            self._render_table(self._items)
            self.notify("Live updates off.")

    def action_cycle_interval(self) -> None:
        """Cycle the live-update interval through the fixed choices."""
        if not self.supports_live:
            return
        new_interval = _cycle_interval(self.app)
        if self._live:
            self._start_timer()
        self._render_table(self._items)  # refresh the info-line "every Ns"
        self.notify(f"Live interval: {new_interval}s.")

    def action_filter(self) -> None:
        """Reveal the filter input and focus it."""
        flt = self.query_one(f"#{self._filter_id}", Input)
        flt.add_class("visible")
        flt.value = self._filter
        flt.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Apply the filter live as the user types."""
        if event.input.id == self._filter_id:
            self._filter = event.value.strip()
            self._render_table(self._items)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Dismiss the filter input on Enter, keeping the filter applied."""
        if event.input.id == self._filter_id:
            self._close_filter(clear=False)

    def on_key(self, event: events.Key) -> None:
        """Escape while the filter is focused clears it and returns to the table."""
        if event.key != "escape":
            return
        flt = self.query_one(f"#{self._filter_id}", Input)
        if flt.has_focus:
            event.stop()
            self._close_filter(clear=True)

    def _close_filter(self, *, clear: bool) -> None:
        """Hide the filter input and return focus to the table."""
        flt = self.query_one(f"#{self._filter_id}", Input)
        if clear:
            flt.value = ""
            self._filter = ""
            self._render_table(self._items)
        flt.remove_class("visible")
        self.query_one(f"#{self._table_id}", DataTable).focus()

    # --- Detail (Enter) ---

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Open the detail view for the selected row (subclasses override _show_detail)."""
        if event.data_table.id == self._table_id:
            self.action_show_detail()

    def action_show_detail(self) -> None:
        """Show details for the selected row. Subclasses override."""


class ProcessListView(LiveTableView):
    """Process List section — a live, filterable view of active sessions."""

    BINDINGS = [
        *LiveTableView.LIVE_BINDINGS,
        Binding("s", "toggle_sleeping", "Hide Sleeping", key_display="S"),
        Binding("k", "kill_query", "Kill Query", key_display="k"),
        Binding("K", "kill_connection", "Kill Conn", key_display="K"),
        Binding("w", "open_in_workspace", "To Workspace", key_display="W"),
    ]

    id_prefix = "process"
    columns = tuple(PROCESS_COLUMNS)
    filter_placeholder = "Filter (user, host, db, state, query) — Enter to keep, Esc to clear"
    noun = "sessions"

    def __init__(self) -> None:
        """Initialize process list state."""
        super().__init__()
        self._hide_sleeping: bool = False

    # --- Data hooks ---

    def _fetch(self) -> list[object]:
        conn_result = self.app.db_connection  # type: ignore[attr-defined]
        server_info = getattr(self.app, "server_info", None)
        return list(fetch_processes(conn_result.connection, server_info))

    def _row_key(self, item: object) -> str:
        return str(item.id)  # type: ignore[attr-defined]

    def _row_cells(self, item: object) -> list[Text]:
        """Build styled cells for a process row."""
        from mydba_tui.renderers.table import styled_cell

        proc: ProcessRow = item  # type: ignore[assignment]
        info = proc.info or ""
        if len(info) > _INFO_TRUNCATE:
            info = info[:_INFO_TRUNCATE] + "…"
        state = proc.state or ""
        if len(state) > _STATE_TRUNCATE:
            state = state[:_STATE_TRUNCATE] + "…"
        cmd_style = "dim" if proc.command == "Sleep" else ""
        return [
            styled_cell(proc.id),
            styled_cell(proc.user),
            styled_cell(proc.host),
            styled_cell(proc.db),
            Text(proc.command, style=cmd_style),
            styled_cell(proc.time),
            styled_cell(state),
            styled_cell(proc.program),
            Text(info),
        ]

    def _matches(self, item: object, needle: str) -> bool:
        proc: ProcessRow = item  # type: ignore[assignment]
        haystack = " ".join(
            str(v)
            for v in (
                proc.id,
                proc.user,
                proc.host,
                proc.db,
                proc.command,
                proc.state,
                proc.program,
                proc.info,
            )
        ).lower()
        return needle.lower() in haystack

    def _pre_filter(self, items: list[object]) -> list[object]:
        if self._hide_sleeping:
            return [it for it in items if it.command != "Sleep"]  # type: ignore[attr-defined]
        return items

    def _extra_flags(self) -> list[str]:
        return ["hiding sleeping"] if self._hide_sleeping else []

    def _selected_process(self) -> ProcessRow | None:
        item = self._selected_item()
        return item  # type: ignore[return-value]

    # --- Actions ---

    def action_toggle_sleeping(self) -> None:
        """Toggle hiding of sleeping connections."""
        self._hide_sleeping = not self._hide_sleeping
        self._render_table(self._items)

    def action_kill_query(self) -> None:
        """Kill the running query of the selected session (keeps connection)."""
        self._confirm_kill(query_only=True)

    def action_kill_connection(self) -> None:
        """Kill the selected session entirely (drops the connection)."""
        self._confirm_kill(query_only=False)

    def _confirm_kill(self, *, query_only: bool) -> None:
        """Confirm and then terminate the selected session or its query."""
        proc = self._selected_process()
        if proc is None:
            self.notify("No session selected.", severity="warning")
            return

        own_id = getattr(getattr(self.app, "server_info", None), "connection_id", 0)
        if own_id and proc.id == own_id:
            self.notify("Refusing to kill your own session.", severity="warning")
            return

        verb = "Kill query on" if query_only else "Kill connection"
        snippet = (proc.info or "").strip()
        if len(snippet) > 60:
            snippet = snippet[:60] + "…"
        detail = f" running: {snippet}" if snippet else ""
        message = f"{verb} session {proc.id} (user {proc.user}){detail}?"

        def on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self._run_kill(proc.id, query_only=query_only)

        self.app.push_screen(ConfirmDialog(message), callback=on_confirm)

    def _run_kill(self, process_id: int, *, query_only: bool) -> None:
        """Execute the KILL on the UI thread, then refresh."""
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self._show_message("[yellow]Not connected to a database.[/yellow]")
            return

        try:
            kill_session(conn_result.connection, process_id, query_only=query_only)
        except Exception as e:
            self.notify(f"Kill failed: {e}", severity="error")
            return

        what = "query" if query_only else "connection"
        self.notify(f"Killed {what} for session {process_id}.")
        self.action_refresh()

    def action_show_detail(self) -> None:
        """Show the full details (all fields + query) of the selected session."""
        proc = self._selected_process()
        if proc is None:
            self.notify("No session selected.", severity="warning")
            return
        self.app.push_screen(_SessionDetailScreen(proc))

    def action_open_in_workspace(self) -> None:
        """Open the selected session's query in the SQL Workspace."""
        proc = self._selected_process()
        if proc is None:
            self.notify("No session selected.", severity="warning")
            return
        if not (proc.info or "").strip():
            self.notify("No query for this session.", severity="information")
            return

        text = _build_workspace_snippet(proc)
        try:
            workspace = self.app.get_screen("workspace", WorkspaceScreen)
        except Exception:
            self.notify("SQL Workspace unavailable.", severity="error")
            return
        workspace.load_query(text)
        self.app.push_screen("workspace")


class ConnectionsView(LiveTableView):
    """Connections section — live connection counts grouped by (user, host)."""

    BINDINGS = [*LiveTableView.LIVE_BINDINGS]

    id_prefix = "conn"
    columns = ("User", "Host", "Connections")
    filter_placeholder = "Filter (user or host) — Enter to keep, Esc to clear"
    noun = "groups"

    def _fetch(self) -> list[object]:
        conn_result = self.app.db_connection  # type: ignore[attr-defined]
        server_info = getattr(self.app, "server_info", None)
        return list(fetch_connection_stats(conn_result.connection, server_info))

    def _row_key(self, item: object) -> str:
        stat: ConnectionStat = item  # type: ignore[assignment]
        return f"{stat.user}\x00{stat.host}"

    def _row_cells(self, item: object) -> list[Text]:
        from mydba_tui.renderers.table import styled_cell

        stat: ConnectionStat = item  # type: ignore[assignment]
        return [
            styled_cell(stat.user),
            styled_cell(stat.host),
            styled_cell(stat.count),
        ]

    def _matches(self, item: object, needle: str) -> bool:
        stat: ConnectionStat = item  # type: ignore[assignment]
        return needle in stat.user.lower() or needle in stat.host.lower()

    def _update_info(self, shown: int, total: int) -> None:
        """Info line shows group counts plus total connections."""
        visible: list[ConnectionStat] = self._visible_items()  # type: ignore[assignment]
        all_stats: list[ConnectionStat] = self._items  # type: ignore[assignment]
        total_conns = sum(s.count for s in all_stats)
        shown_conns = sum(s.count for s in visible)
        flags = []
        if self.supports_live:
            if self._live:
                flags.append(f"[green]● live[/green] every {_current_interval(self.app)}s")
            else:
                flags.append("[dim]○ live off[/dim]")
        if self._filter:
            flags.append(f"filter: '{self._filter}'")
        suffix = f"  ({', '.join(flags)})" if flags else ""
        self._show_message(
            f"[bold]{shown}[/bold] of {total} groups, "
            f"{shown_conns} of {total_conns} connections{suffix}"
        )


class TransactionsView(LiveTableView):
    """Transactions section — active InnoDB transactions, longest-running first."""

    BINDINGS = [
        *LiveTableView.LIVE_BINDINGS,
        Binding("k", "kill_connection", "Kill Conn", key_display="K"),
        Binding("w", "open_in_workspace", "To Workspace", key_display="W"),
    ]

    id_prefix = "trx"
    columns = tuple(TRANSACTION_COLUMNS)
    filter_placeholder = "Filter (user, host, db, state, query) — Enter to keep, Esc to clear"
    noun = "transactions"

    _QUERY_TRUNCATE = 80

    def _fetch(self) -> list[object]:
        conn_result = self.app.db_connection  # type: ignore[attr-defined]
        return list(fetch_transactions(conn_result.connection))

    def _row_key(self, item: object) -> str:
        return str(item.trx_id)  # type: ignore[attr-defined]

    def _row_cells(self, item: object) -> list[Text]:
        from mydba_tui.renderers.table import styled_cell

        trx: TransactionRow = item  # type: ignore[assignment]
        query = trx.query or ""
        if len(query) > self._QUERY_TRUNCATE:
            query = query[: self._QUERY_TRUNCATE] + "…"
        return [
            styled_cell(trx.trx_id),
            styled_cell(trx.conn_id),
            styled_cell(trx.user),
            styled_cell(trx.host),
            styled_cell(trx.db),
            styled_cell(trx.state),
            styled_cell(_format_seconds(trx.age_seconds)),
            styled_cell(trx.rows_locked),
            Text(query),
        ]

    def _matches(self, item: object, needle: str) -> bool:
        trx: TransactionRow = item  # type: ignore[assignment]
        haystack = " ".join(
            str(v)
            for v in (
                trx.trx_id,
                trx.conn_id,
                trx.user,
                trx.host,
                trx.db,
                trx.state,
                trx.query,
            )
        ).lower()
        return needle in haystack

    def _selected_transaction(self) -> TransactionRow | None:
        item = self._selected_item()
        return item  # type: ignore[return-value]

    # --- Actions ---

    def action_show_detail(self) -> None:
        """Show the full details of the selected transaction."""
        trx = self._selected_transaction()
        if trx is None:
            self.notify("No transaction selected.", severity="warning")
            return
        self.app.push_screen(_TransactionDetailScreen(trx))

    def action_open_in_workspace(self) -> None:
        """Open the selected transaction's query in the SQL Workspace."""
        trx = self._selected_transaction()
        if trx is None:
            self.notify("No transaction selected.", severity="warning")
            return
        if not (trx.query or "").strip():
            self.notify("No query for this transaction.", severity="information")
            return

        text = _build_transaction_snippet(trx)
        try:
            workspace = self.app.get_screen("workspace", WorkspaceScreen)
        except Exception:
            self.notify("SQL Workspace unavailable.", severity="error")
            return
        workspace.load_query(text)
        self.app.push_screen("workspace")

    def action_kill_connection(self) -> None:
        """Kill the connection running the selected transaction (with confirm)."""
        trx = self._selected_transaction()
        if trx is None:
            self.notify("No transaction selected.", severity="warning")
            return
        if trx.conn_id == 0:
            self.notify("No connection id for this transaction.", severity="warning")
            return

        own_id = getattr(getattr(self.app, "server_info", None), "connection_id", 0)
        if own_id and trx.conn_id == own_id:
            self.notify("Refusing to kill your own session.", severity="warning")
            return

        message = (
            f"Kill connection {trx.conn_id} (user {trx.user}) holding transaction {trx.trx_id}?"
        )

        def on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self._run_kill(trx.conn_id)

        self.app.push_screen(ConfirmDialog(message), callback=on_confirm)

    def _run_kill(self, conn_id: int) -> None:
        """Kill the connection on the UI thread, then refresh."""
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self._show_message("[yellow]Not connected to a database.[/yellow]")
            return

        try:
            kill_session(conn_result.connection, conn_id, query_only=False)
        except Exception as e:
            self.notify(f"Kill failed: {e}", severity="error")
            return

        self.notify(f"Killed connection {conn_id}.")
        self.action_refresh()


class LocksView(LiveTableView):
    """Locks section — InnoDB row-lock waits (who is blocked by whom)."""

    BINDINGS = [
        *LiveTableView.LIVE_BINDINGS,
        Binding("k", "kill_blocker", "Kill Blocker", key_display="K"),
    ]

    id_prefix = "locks"
    columns = tuple(LOCK_COLUMNS)
    filter_placeholder = "Filter (user, table, query) — Enter to keep, Esc to clear"
    noun = "lock waits"

    _QUERY_TRUNCATE = 60

    def _fetch(self) -> list[object]:
        conn_result = self.app.db_connection  # type: ignore[attr-defined]
        return list(fetch_lock_waits(conn_result.connection))

    def _row_key(self, item: object) -> str:
        lw: LockWait = item  # type: ignore[assignment]
        return f"{lw.waiting_pid}\x00{lw.blocking_pid}"

    def _row_cells(self, item: object) -> list[Text]:
        from mydba_tui.renderers.table import styled_cell

        lw: LockWait = item  # type: ignore[assignment]
        table = (
            f"{lw.locked_schema}.{lw.locked_table}" if lw.locked_schema or lw.locked_table else ""
        )
        waiting = self._truncate(lw.waiting_query)
        blocking = self._truncate(lw.blocking_query) or "(idle)"
        return [
            styled_cell(_format_seconds(lw.wait_age_secs)),
            styled_cell(table),
            styled_cell(lw.waiting_pid),
            styled_cell(lw.waiting_user),
            styled_cell(lw.waiting_lock_mode),
            Text(waiting),
            styled_cell(lw.blocking_pid),
            styled_cell(lw.blocking_user),
            styled_cell(lw.blocking_lock_mode),
            Text(blocking),
        ]

    def _truncate(self, text: str) -> str:
        text = text or ""
        return text if len(text) <= self._QUERY_TRUNCATE else text[: self._QUERY_TRUNCATE] + "…"

    def _matches(self, item: object, needle: str) -> bool:
        lw: LockWait = item  # type: ignore[assignment]
        haystack = " ".join(
            str(v)
            for v in (
                lw.waiting_pid,
                lw.waiting_user,
                lw.waiting_lock_mode,
                lw.waiting_query,
                lw.blocking_pid,
                lw.blocking_user,
                lw.blocking_lock_mode,
                lw.blocking_query,
                lw.locked_schema,
                lw.locked_table,
            )
        ).lower()
        return needle in haystack

    def _selected_lock(self) -> LockWait | None:
        item = self._selected_item()
        return item  # type: ignore[return-value]

    # --- Actions ---

    def action_show_detail(self) -> None:
        """Show the full waiting/blocking detail of the selected lock wait."""
        lw = self._selected_lock()
        if lw is None:
            self.notify("No lock wait selected.", severity="warning")
            return
        self.app.push_screen(_LockDetailScreen(lw))

    def action_kill_blocker(self) -> None:
        """Kill the blocking connection to release the selected lock wait."""
        lw = self._selected_lock()
        if lw is None:
            self.notify("No lock wait selected.", severity="warning")
            return
        if lw.blocking_pid == 0:
            self.notify("No blocking connection id.", severity="warning")
            return

        own_id = getattr(getattr(self.app, "server_info", None), "connection_id", 0)
        if own_id and lw.blocking_pid == own_id:
            self.notify("Refusing to kill your own session.", severity="warning")
            return

        message = (
            f"Kill blocking connection {lw.blocking_pid} "
            f"(user {lw.blocking_user}) to release waiting session {lw.waiting_pid}?"
        )

        def on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self._run_kill(lw.blocking_pid)

        self.app.push_screen(ConfirmDialog(message), callback=on_confirm)

    def _run_kill(self, conn_id: int) -> None:
        """Kill the connection on the UI thread, then refresh."""
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self._show_message("[yellow]Not connected to a database.[/yellow]")
            return

        try:
            kill_session(conn_result.connection, conn_id, query_only=False)
        except Exception as e:
            self.notify(f"Kill failed: {e}", severity="error")
            return

        self.notify(f"Killed blocking connection {conn_id}.")
        self.action_refresh()


class MetadataLocksView(LiveTableView):
    """Metadata Locks section — table MDL waits (who is blocked by whom)."""

    BINDINGS = [
        *LiveTableView.LIVE_BINDINGS,
        Binding("k", "kill_blocker", "Kill Blocker", key_display="K"),
    ]

    id_prefix = "mdl"
    columns = tuple(MDL_COLUMNS)
    filter_placeholder = "Filter (account, object, query) — Enter to keep, Esc to clear"
    noun = "metadata lock waits"

    _QUERY_TRUNCATE = 60

    def _fetch(self) -> list[object]:
        conn_result = self.app.db_connection  # type: ignore[attr-defined]
        return list(fetch_metadata_lock_waits(conn_result.connection))

    def _row_key(self, item: object) -> str:
        m: MetadataLockWait = item  # type: ignore[assignment]
        return f"{m.waiting_pid}\x00{m.blocking_pid}\x00{m.object_schema}.{m.object_name}"

    def _row_cells(self, item: object) -> list[Text]:
        from mydba_tui.renderers.table import styled_cell

        m: MetadataLockWait = item  # type: ignore[assignment]
        obj = f"{m.object_schema}.{m.object_name}".strip(".")
        query = m.waiting_query or ""
        if len(query) > self._QUERY_TRUNCATE:
            query = query[: self._QUERY_TRUNCATE] + "…"
        return [
            styled_cell(_format_seconds(m.wait_age_secs)),
            styled_cell(obj),
            styled_cell(m.waiting_pid),
            styled_cell(m.waiting_account),
            styled_cell(m.waiting_lock_type),
            Text(query),
            styled_cell(m.blocking_pid),
            styled_cell(m.blocking_account),
            styled_cell(m.blocking_lock_type),
        ]

    def _matches(self, item: object, needle: str) -> bool:
        m: MetadataLockWait = item  # type: ignore[assignment]
        haystack = " ".join(
            str(v)
            for v in (
                m.waiting_pid,
                m.waiting_account,
                m.waiting_lock_type,
                m.waiting_query,
                m.blocking_pid,
                m.blocking_account,
                m.blocking_lock_type,
                m.object_schema,
                m.object_name,
            )
        ).lower()
        return needle in haystack

    def _selected_mdl(self) -> MetadataLockWait | None:
        item = self._selected_item()
        return item  # type: ignore[return-value]

    # --- Actions ---

    def action_show_detail(self) -> None:
        """Show the full detail of the selected metadata-lock wait."""
        m = self._selected_mdl()
        if m is None:
            self.notify("No metadata lock wait selected.", severity="warning")
            return
        self.app.push_screen(_MetadataLockDetailScreen(m))

    def action_kill_blocker(self) -> None:
        """Kill the blocking connection to release the selected MDL wait."""
        m = self._selected_mdl()
        if m is None:
            self.notify("No metadata lock wait selected.", severity="warning")
            return
        if m.blocking_pid == 0:
            self.notify("No blocking connection id.", severity="warning")
            return

        own_id = getattr(getattr(self.app, "server_info", None), "connection_id", 0)
        if own_id and m.blocking_pid == own_id:
            self.notify("Refusing to kill your own session.", severity="warning")
            return

        message = (
            f"Kill blocking connection {m.blocking_pid} "
            f"({m.blocking_account}) to release waiting session {m.waiting_pid}?"
        )

        def on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self._run_kill(m.blocking_pid)

        self.app.push_screen(ConfirmDialog(message), callback=on_confirm)

    def _run_kill(self, conn_id: int) -> None:
        """Kill the connection on the UI thread, then refresh."""
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self._show_message("[yellow]Not connected to a database.[/yellow]")
            return

        try:
            kill_session(conn_result.connection, conn_id, query_only=False)
        except Exception as e:
            self.notify(f"Kill failed: {e}", severity="error")
            return

        self.notify(f"Killed blocking connection {conn_id}.")
        self.action_refresh()


class UsersView(LiveTableView):
    """Users section — accounts grouped by role, with grants on demand."""

    # No live updates for Users — only manual refresh and filter. Overriding
    # BINDINGS drops the inherited L (live) and I (interval) keys so they don't
    # appear in the footer for a tab that never auto-refreshes.
    BINDINGS = [
        Binding("r", "refresh", "Refresh", key_display="R", priority=True),
        Binding("slash", "filter", "Filter", key_display="/"),
    ]

    id_prefix = "users"
    columns = tuple(USER_COLUMNS)
    filter_placeholder = "Filter (group, user, host) — Enter to keep, Esc to clear"
    noun = "accounts"
    supports_live = False  # accounts change rarely; load once, manual R only

    # Palette for auto-assigning group colours when the SQL leaves group_color
    # empty. Chosen to be readable and to avoid the red/green used elsewhere
    # for errors/success. Cycled per distinct group in first-seen order.
    _GROUP_PALETTE = (
        "cyan",
        "magenta",
        "yellow",
        "dodger_blue1",
        "orange1",
        "spring_green2",
        "hot_pink",
        "gold1",
        "turquoise2",
        "purple",
    )

    def _fetch(self) -> list[object]:
        conn_result = self.app.db_connection  # type: ignore[attr-defined]
        return list(fetch_users(conn_result.connection))

    def _row_key(self, item: object) -> str:
        acc: UserAccount = item  # type: ignore[assignment]
        return f"{acc.user}\x00{acc.host}"

    def _group_colors(self) -> dict[str, str]:
        """Map each distinct group to a colour.

        Uses the SQL-provided colour when present; otherwise auto-assigns from
        the palette in first-seen (i.e. display) order so colours are stable
        within a refresh and distinct across groups.
        """
        colors: dict[str, str] = {}
        palette_idx = 0
        for it in self._items:
            acc: UserAccount = it  # type: ignore[assignment]
            if acc.group in colors:
                continue
            if acc.group_color.strip():
                colors[acc.group] = acc.group_color.strip()
            else:
                colors[acc.group] = self._GROUP_PALETTE[palette_idx % len(self._GROUP_PALETTE)]
                palette_idx += 1
        return colors

    def _row_cells(self, item: object) -> list[Text]:
        from mydba_tui.renderers.table import styled_cell

        acc: UserAccount = item  # type: ignore[assignment]
        group_color = self._group_colors().get(acc.group, "")
        group_cell = Text(acc.group, style=group_color) if group_color else Text(acc.group)
        locked = "yes" if acc.locked else ""
        expired = "yes" if acc.password_expired else ""
        return [
            group_cell,
            styled_cell(acc.user),
            styled_cell(acc.host),
            Text(locked, style="red" if acc.locked else "dim"),
            Text(expired, style="yellow" if acc.password_expired else "dim"),
            styled_cell(acc.password_last_changed),
            styled_cell(acc.plugin),
        ]

    def _matches(self, item: object, needle: str) -> bool:
        acc: UserAccount = item  # type: ignore[assignment]
        haystack = " ".join(str(v) for v in (acc.group, acc.user, acc.host, acc.plugin)).lower()
        return needle in haystack

    def _selected_account(self) -> UserAccount | None:
        item = self._selected_item()
        return item  # type: ignore[return-value]

    def action_show_detail(self) -> None:
        """Show account summary plus its grants (fetched on demand)."""
        acc = self._selected_account()
        if acc is None:
            self.notify("No account selected.", severity="warning")
            return
        self.app.push_screen(_UserDetailScreen(acc))


class ReplicationView(Vertical):
    """Replication section — a read-only unified cockpit.

    Role- and vendor-aware: shows a health banner, per-channel replica status
    with a live lag graph, primary/binlog state, GTID state, and Galera/PXC
    cluster state. Auto-refreshes (pausable); read-only.
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh", key_display="R", priority=True),
        Binding("l", "toggle_live", "Live On/Off", key_display="L"),
        Binding("i", "cycle_interval", "Interval", key_display="I"),
    ]

    # Focusable so its bindings surface in the Footer and Tab moves focus into
    # the content (matching the table-based tabs). The body is Static-only, so
    # without this the view could never take focus.
    can_focus = True

    DEFAULT_CSS = """
    ReplicationView {
        height: 1fr;
        overflow-y: auto;
        border: round $panel;
    }

    ReplicationView:focus {
        /* Highlight the pane while it holds focus so it's obvious the tab's
           keys (R/P) are active and arrows scroll the body rather than the
           tab bar. */
        border: round $accent;
        background: $boost;
    }

    ReplicationView #repl-banner {
        height: auto;
        padding: 1 2 0 2;
        text-style: bold;
    }

    ReplicationView #repl-status {
        height: auto;
        padding: 0 2 1 2;
        color: $text-muted;
        text-align: right;
    }

    ReplicationView #repl-lag {
        height: auto;
        margin: 0 2 1 2;
    }

    ReplicationView #repl-body {
        height: auto;
        padding: 0 2 1 2;
    }
    """

    # How much history the lag graph keeps, as a duration. The sample cap is
    # derived from this and the refresh interval (e.g. 30 min at a 3s interval
    # is 600 samples), so the window is a real 30 minutes regardless of the
    # configured refresh rate.
    _LAG_WINDOW_SECONDS = 30 * 60

    def __init__(self) -> None:
        """Initialize replication view state."""
        super().__init__()
        # Live updates start OFF. Each full fetch runs several queries on the
        # single (UI-thread-only) connection, so the tab loads once on open;
        # the user turns on live updates with L (or refreshes on demand with R).
        self._live: bool = False
        self._refresh_timer: Timer | None = None
        self._lag_samples: list[int] = []
        self._loaded_once: bool = False
        self._last_info: ReplicationInfo | None = None
        self._interval: int = 5
        self._fetching: bool = False

    def compose(self) -> ComposeResult:
        """Build the cockpit layout."""
        yield Static("", id="repl-banner")
        yield Static("", id="repl-status")
        yield Static("", id="repl-lag")
        yield Static("", id="repl-body")

    def on_mount(self) -> None:
        """Set up the (initially stopped) refresh timer and the focus title.

        The first fetch happens on tab activation, not on mount — the tab is
        not the default one, so querying on mount would run ~13 queries for a
        tab the user may never open. Auto-refresh is off until the user enables
        it with P; the timer only fetches while live AND this tab is active.
        """
        self._loaded_once = False
        self._interval = _current_interval(self.app)
        self.border_title = "Replication"
        self._render_status_line()
        self._start_timer()

    def _start_timer(self) -> None:
        """(Re)start the auto-refresh timer at the current interval."""
        self._interval = _current_interval(self.app)
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
        self._refresh_timer = self.set_interval(self._interval, self._on_refresh_tick)

    def refresh_data(self) -> None:
        """Public hook called when the tab is shown.

        Re-entering the tab is instant: if data is already loaded, re-render it
        from cache. Only the first activation triggers a (deferred) fetch.
        """
        if self._loaded_once and self._last_info is not None:
            self._render_view(self._last_info)
            return
        self.action_refresh()

    def on_focus(self) -> None:
        """Reflect focus in the pane title."""
        self.border_title = "Replication  (focused — R refresh · L live)"

    def on_blur(self) -> None:
        """Reflect loss of focus in the pane title."""
        self.border_title = "Replication"

    def _on_refresh_tick(self) -> None:
        """Timer callback — fetch only when live and this tab is active."""
        if not self._live or not _view_is_active_tab(self):
            return
        self.action_refresh()

    def action_toggle_live(self) -> None:
        """Turn live auto-refresh on or off."""
        self._live = not self._live
        if self._live:
            self.notify(f"Live updates on — refreshing every {self._interval}s.")
            # Fetch immediately so the graph starts moving without waiting a tick.
            self.action_refresh()
        else:
            self.notify("Live updates off.")
        self._render_status_line()

    def action_cycle_interval(self) -> None:
        """Cycle the auto-refresh interval through the fixed choices."""
        new_interval = _cycle_interval(self.app)
        self._start_timer()
        self._render_status_line()
        self.notify(f"Auto-refresh interval: {new_interval}s.")

    def action_refresh(self) -> None:
        """Reload replication state.

        The single shared mysql-connector connection is not thread-safe (its C
        backend crashes the interpreter if used from two threads), so the fetch
        runs on the UI thread — the same rule the rest of Administration and the
        object browser follow. To avoid a frozen-looking first paint, the very
        first load shows a loading banner and defers the fetch one tick so the
        banner paints first. A re-entrancy guard prevents timer ticks from
        stacking fetches on top of one another.
        """
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self.query_one("#repl-banner", Static).update(
                "[yellow]Not connected to a database.[/yellow]"
            )
            return

        # Don't stack fetches: if one is already scheduled/running, skip.
        if self._fetching:
            return
        self._fetching = True

        if not self._loaded_once:
            self.query_one("#repl-banner", Static).update(
                "[cyan]⟳ Loading replication status…[/cyan]"
            )
            # Defer one tick so the loading banner paints before the fetch runs.
            self.set_timer(0.05, self._do_fetch)
        else:
            self.call_after_refresh(self._do_fetch)

    def _do_fetch(self) -> None:
        """Run the queries (on the UI thread) and render."""
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self._fetching = False
            return

        server_info = getattr(self.app, "server_info", None)
        try:
            info = fetch_replication(conn_result.connection, server_info)
        except Exception as e:
            self.query_one("#repl-banner", Static).update(f"[red]Error: {e}[/red]")
            self._fetching = False
            return

        self._loaded_once = True
        self._last_info = info
        self._update_lag_samples(info)
        self._render_view(info)
        self._fetching = False

    @property
    def _lag_window(self) -> int:
        """Max samples to keep = window duration / refresh interval."""
        return max(self._LAG_WINDOW_SECONDS // max(self._interval, 1), 2)

    def _update_lag_samples(self, info: ReplicationInfo) -> None:
        """Append the worst current replica lag to the rolling window."""
        lags = [c.seconds_behind for c in info.channels if c.seconds_behind is not None]
        if not lags:
            return
        self._lag_samples.append(max(lags))
        cap = self._lag_window
        if len(self._lag_samples) > cap:
            self._lag_samples = self._lag_samples[-cap:]

    _LEVEL_COLOR = {
        "healthy": "green",
        "warn": "yellow",
        "error": "red",
        "info": "cyan",
    }

    def _render_view(self, info: ReplicationInfo) -> None:
        """Render banner, refresh status, lag graph, and the structured body."""
        verdict = compute_verdict(info)
        color = self._LEVEL_COLOR.get(verdict.level, "white")
        # Restore the original banner styling (colored verdict, no extra text).
        self.query_one("#repl-banner", Static).update(f"[{color}]● {verdict.text}[/{color}]")

        # Refresh status line: tells the reader how often the graph updates, or
        # that auto-refresh is paused. Its own dim, right-aligned line so it is
        # always visible above the graph regardless of banner width.
        self._render_status_line()

        # Lag graph: shown whenever this host is a replica (even when lag is a
        # flat 0, so the graph reads as "healthy and working"). Hidden only on
        # non-replicas, where there is nothing to plot.
        lag_widget = self.query_one("#repl-lag", Static)
        if self._lag_samples:
            lag_widget.display = True
            width = max(self.size.width - 4, 20)
            lag_widget.update(
                _render_lag_chart(
                    self._lag_samples, width, 6, self._interval, self._LAG_WINDOW_SECONDS
                )
            )
        else:
            lag_widget.display = False

        self.query_one("#repl-body", Static).update(self._build_body(info))

    def _status_markup(self) -> str:
        """Refresh-status text: live cadence, or a hint to enable it."""
        if self._live:
            return f"[green]● live[/green] · every {self._interval}s  ·  L to stop · R to refresh"
        return "[dim]○ live off[/dim]  ·  L to start live updates · R to refresh once"

    def _render_status_line(self) -> None:
        """Update the refresh-status line (interval or paused)."""
        self.query_one("#repl-status", Static).update(self._status_markup())

    @staticmethod
    def _kv_block(rows: list[tuple[str, str]]) -> list[str]:
        """Format (label, value) pairs as an aligned block (vertical/\\G style).

        Labels are right-aligned to a common width and separated from values by
        a colon, so every value starts in the same column regardless of label
        length. Rich markup in values does not affect the label alignment (only
        the label text is measured).
        """
        if not rows:
            return []
        width = max(len(label) for label, _ in rows)
        return [f"  {label:>{width}} : {value}" for label, value in rows]

    def _build_body(self, info: ReplicationInfo) -> str:
        """Build the structured body as Rich markup."""
        parts: list[str] = []

        # Replica channels (this host as a replica / middle of a chain).
        for ch in info.channels:
            name = f" (channel '{ch.channel}')" if ch.channel else ""
            parts.append(f"[bold cyan]Replica{name}[/bold cyan]")
            io_c = "green" if ch.io_running.lower() == "yes" else "red"
            sql_c = "green" if ch.sql_running.lower() == "yes" else "red"
            if ch.seconds_behind is None:
                lag = "[red]NULL (not replicating)[/red]"
            else:
                trend = lag_trend(self._lag_samples)
                lag = f"{ch.seconds_behind}s {trend}"

            rows: list[tuple[str, str]] = [
                ("IO thread", f"[{io_c}]{ch.io_running or '—'}[/{io_c}]"),
                ("SQL thread", f"[{sql_c}]{ch.sql_running or '—'}[/{sql_c}]"),
                ("Lag", lag),
                ("Source", f"{ch.source_host or '—'}:{ch.source_port or '—'}"),
                ("Source log", f"{ch.source_log_file or '—'} @ {ch.read_source_log_pos or '—'}"),
                (
                    "Applied",
                    f"{ch.relay_source_log_file or '—'} @ {ch.exec_source_log_pos or '—'}",
                ),
            ]
            # Retrieved-but-not-yet-applied work on the current source file.
            unapplied = ch.unapplied_bytes
            if unapplied is not None:
                rows.append(("Unapplied", f"{_format_bytes(unapplied)} (retrieved, not applied)"))
            rows.append(("Relay log", f"{ch.relay_log_file or '—'} @ {ch.relay_log_pos or '—'}"))
            relay_space = _format_bytes(ch.relay_log_space) if ch.relay_log_space else "—"
            rows.append(("Relay log disk usage", relay_space))
            # Applier threads (parallel replication).
            if ch.parallel_workers > 0:
                busy = f"{ch.busy_workers} busy" if ch.busy_workers else "idle"
                ptype = f" [{ch.parallel_type}]" if ch.parallel_type else ""
                rows.append(("Applier", f"{ch.parallel_workers} workers{ptype}, {busy}"))
            else:
                rows.append(("Applier", "single-threaded"))
            rows.append(("Auto-position", "on" if ch.auto_position else "off"))
            if ch.last_io_error.strip():
                rows.append(("IO error", f"[red]{ch.last_io_errno}: {ch.last_io_error}[/red]"))
            if ch.last_sql_error.strip():
                rows.append(("SQL error", f"[red]{ch.last_sql_errno}: {ch.last_sql_error}[/red]"))
            parts.extend(self._kv_block(rows))
            parts.append("")

        # Binary logs of the local host (a replica may also write its own
        # binlogs for chained replication, so this is not necessarily "primary").
        p = info.primary
        if p.is_primary or p.binlog_file:
            parts.append("[bold cyan]Binary Logs[/bold cyan]")
            binlog_rows: list[tuple[str, str]] = []
            if p.binlog_file:
                binlog_rows.append(("Current binlog", f"{p.binlog_file} @ {p.binlog_pos}"))
            if p.binlog_format:
                binlog_rows.append(("Format", p.binlog_format))
            if p.binlog_row_image:
                binlog_rows.append(("Row image", p.binlog_row_image))
            if p.binlog_row_metadata:
                binlog_rows.append(("Row metadata", p.binlog_row_metadata))
            if p.binlog_count:
                binlog_rows.append(
                    ("Binary logs", f"{p.binlog_count} ({_format_bytes(p.binlog_total_bytes)})")
                )
            parts.extend(self._kv_block(binlog_rows))
            parts.append("")

        # Connected replicas (downstream) — valid on a primary or a chain node.
        if p.replicas:
            n = len(p.replicas)
            parts.append(f"[bold cyan]Connected Replicas ({n})[/bold cyan]")
            for r in p.replicas:
                parts.append(f"  • server_id {r.server_id or '—'}  {r.host or '—'}:{r.port or '—'}")
            parts.append("")

        # GTID — sets shown on their own lines (they can be long / multi-line).
        if info.gtid.enabled:
            parts.append("[bold cyan]GTID[/bold cyan]")
            for label, value in (
                ("Retrieved", info.gtid.retrieved),
                ("Executed", info.gtid.executed),
                ("Purged", info.gtid.purged),
            ):
                parts.append(f"  [bold]{label}[/bold]")
                parts.append(f"    {rich_escape(value) if value else '—'}")
            parts.append("")

        # Cluster (Galera / PXC).
        c = info.cluster
        if c.enabled:
            parts.append("[bold cyan]Galera / PXC Cluster[/bold cyan]")
            synced = c.local_state.lower() == "synced"
            state_c = "green" if synced else "yellow"
            parts.extend(
                self._kv_block(
                    [
                        ("Cluster", c.cluster_name or "—"),
                        ("Status", c.cluster_status or "—"),
                        ("Local state", f"[{state_c}]{c.local_state or '—'}[/{state_c}]"),
                        ("Nodes", c.cluster_size or "—"),
                        ("Flow control paused", c.flow_control_paused or "0"),
                    ]
                )
            )
            parts.append("")

        if not parts:
            parts.append("[dim]No replication configured on this server.[/dim]")

        return "\n".join(parts)


class KeyValueView(Vertical):
    """Base for a filterable, refreshable key/value table section.

    Subclasses supply the section specifics: a DOM id prefix, column headers,
    a plural noun for the info line, and a fetch function that returns sorted
    ``(name, value)`` pairs. The base provides the table, client-side filter
    (matching name and value), manual refresh, and a full-value detail modal.
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh", key_display="R", priority=True),
        Binding("slash", "filter", "Filter", key_display="/"),
    ]

    DEFAULT_CSS = """
    KeyValueView {
        height: 1fr;
    }

    KeyValueView .kv-info {
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }

    KeyValueView .kv-table {
        height: 1fr;
    }

    KeyValueView .kv-filter {
        display: none;
        height: auto;
        border: tall $accent;
    }

    KeyValueView .kv-filter.visible {
        display: block;
    }
    """

    # Value truncation in the table; full value shown in the detail modal.
    _VALUE_TRUNCATE = 100

    # --- Subclass configuration (override these) ---
    id_prefix: str = "kv"
    name_column: str = "Name"
    value_column: str = "Value"
    noun: str = "entries"
    load_once: bool = False  # if True, only auto-loads on first tab show

    def _fetch(self, connection: object) -> list[tuple[str, str]]:
        """Return sorted (name, value) pairs. Subclasses must override."""
        raise NotImplementedError

    def __init__(self) -> None:
        """Initialize key/value state."""
        super().__init__()
        self._rows: list[tuple[str, str]] = []
        self._filter: str = ""

    # --- DOM helpers ---

    @property
    def _info_id(self) -> str:
        return f"{self.id_prefix}-info"

    @property
    def _table_id(self) -> str:
        return f"{self.id_prefix}-table"

    @property
    def _filter_id(self) -> str:
        return f"{self.id_prefix}-filter"

    def compose(self) -> ComposeResult:
        """Build the key/value layout."""
        yield Static("", id=self._info_id, classes="kv-info")
        table: DataTable[Text] = DataTable(
            id=self._table_id, classes="kv-table", zebra_stripes=True
        )
        table.cursor_type = "row"
        yield table
        yield Input(
            placeholder="Filter (name or value) — Enter to keep, Esc to clear",
            id=self._filter_id,
            classes="kv-filter",
        )

    def on_mount(self) -> None:
        """Set up the table columns and load once."""
        table = self.query_one(f"#{self._table_id}", DataTable)
        table.add_column(self.name_column, key="name")
        table.add_column(self.value_column, key="value")
        self._load_deferred()

    def refresh_data(self) -> None:
        """Public hook to (re)load data when the tab is shown."""
        if self.load_once and self._rows:
            return
        self._load_deferred()

    def _load_deferred(self) -> None:
        """Paint a loading note, then run the query on the next tick.

        Lets the tab paint before the (sometimes heavy) query runs, so a busy
        server never makes tab switching look frozen. The query stays on the UI
        thread — the shared connection is not thread-safe.
        """
        if not self._rows:
            self.query_one(f"#{self._info_id}", Static).update("[cyan]⟳ Loading…[/cyan]")
            # Short timer so the loading note paints before the query blocks.
            self.set_timer(0.05, self.action_refresh)
        else:
            self.call_after_refresh(self.action_refresh)

    # --- Data loading ---

    def action_refresh(self) -> None:
        """Reload data (synchronous, single-threaded connection)."""
        from mydba_tui.connection import ConnectionResult

        info = self.query_one(f"#{self._info_id}", Static)
        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            info.update("[yellow]Not connected to a database.[/yellow]")
            return

        try:
            rows = self._fetch(conn_result.connection)
        except Exception as e:
            info.update(f"[red]Error: {e}[/red]")
            return

        self._rows = rows
        self._render_table()

    def _render_table(self) -> None:
        """Populate the table with the (filtered) rows."""
        from mydba_tui.renderers.table import styled_cell

        table = self.query_one(f"#{self._table_id}", DataTable)
        table.clear()
        visible = self._visible_rows()
        for name, value in visible:
            display = (
                value if len(value) <= self._VALUE_TRUNCATE else value[: self._VALUE_TRUNCATE] + "…"
            )
            table.add_row(styled_cell(name), styled_cell(display), key=name)

        flags = f"  (filter: '{self._filter}')" if self._filter else ""
        self.query_one(f"#{self._info_id}", Static).update(
            f"[bold]{len(visible)}[/bold] of {len(self._rows)} {self.noun}{flags}"
        )

    def _visible_rows(self) -> list[tuple[str, str]]:
        """Apply the text filter across name and value."""
        if not self._filter:
            return self._rows
        needle = self._filter.lower()
        return [(n, v) for n, v in self._rows if needle in n.lower() or needle in v.lower()]

    # --- Filter ---

    def action_filter(self) -> None:
        """Reveal the filter input and focus it."""
        flt = self.query_one(f"#{self._filter_id}", Input)
        flt.add_class("visible")
        flt.value = self._filter
        flt.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Apply the filter live as the user types."""
        if event.input.id == self._filter_id:
            self._filter = event.value.strip()
            self._render_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Dismiss the filter input on Enter, keeping the filter applied."""
        if event.input.id == self._filter_id:
            self._close_filter(clear=False)

    def on_key(self, event: events.Key) -> None:
        """Escape while the filter is focused clears it and returns to table."""
        if event.key != "escape":
            return
        flt = self.query_one(f"#{self._filter_id}", Input)
        if flt.has_focus:
            event.stop()
            self._close_filter(clear=True)

    def _close_filter(self, *, clear: bool) -> None:
        """Hide the filter input and return focus to the table."""
        flt = self.query_one(f"#{self._filter_id}", Input)
        if clear:
            flt.value = ""
            self._filter = ""
            self._render_table()
        flt.remove_class("visible")
        self.query_one(f"#{self._table_id}", DataTable).focus()

    # --- Detail ---

    def _selected_pair(self) -> tuple[str, str] | None:
        """Return the (name, value) of the selected row, if any."""
        table = self.query_one(f"#{self._table_id}", DataTable)
        if table.row_count == 0:
            return None
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        except Exception:
            return None
        if row_key.value is None:
            return None
        name = str(row_key.value)
        return next(((n, v) for n, v in self._rows if n == name), None)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Show the full value of the selected row on Enter."""
        if event.data_table.id != self._table_id:
            return
        selected = self._selected_pair()
        if selected is None:
            return
        name, value = selected
        self.app.push_screen(_KeyValueDetailScreen(name, value))


class VariablesView(KeyValueView):
    """Variables section — all global variables with client-side filtering."""

    id_prefix = "vars"
    name_column = "Variable"
    value_column = "Value"
    noun = "variables"
    load_once = True  # variables rarely change

    def _fetch(self, connection: object) -> list[tuple[str, str]]:
        """Fetch global variables."""
        return fetch_variables(connection)  # type: ignore[arg-type]


class StatusView(KeyValueView):
    """Status section — all global status counters with client-side filtering."""

    id_prefix = "status"
    name_column = "Status Variable"
    value_column = "Value"
    noun = "status values"
    load_once = False  # counters change; reload each time the tab is shown

    def _fetch(self, connection: object) -> list[tuple[str, str]]:
        """Fetch global status counters."""
        return fetch_status(connection)  # type: ignore[arg-type]


class _SessionDetailScreen(ModalScreen[None]):
    """Modal showing the full details of a session.

    Displays every session field in full (State and the query are truncated in
    the table but shown here untruncated) plus the syntax-highlighted query
    when the session has one.
    """

    BINDINGS = [
        Binding("escape", "close", "Close", key_display="Esc"),
    ]

    CSS = """
    _SessionDetailScreen {
        align: center middle;
        background: $background 80%;
    }

    #detail-container {
        width: 80%;
        max-width: 120;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    #detail-title {
        text-style: bold;
        padding-bottom: 1;
    }

    #detail-meta {
        height: auto;
        padding-bottom: 1;
    }

    #detail-body {
        height: auto;
        max-height: 24;
        overflow-y: auto;
    }
    """

    def __init__(self, proc: ProcessRow) -> None:
        """Initialize with the process whose details are shown."""
        super().__init__()
        self._proc = proc

    def compose(self) -> ComposeResult:
        """Build the detail modal."""
        from mydba_tui.ui.mysql_highlight import highlight_mysql

        proc = self._proc
        meta_lines = [
            f"[bold]Connection Id:[/bold] {proc.id}",
            f"[bold]User:[/bold] {_meta_value(proc.user)}",
            f"[bold]Host:[/bold] {_meta_value(proc.host)}",
            f"[bold]DB:[/bold] {_meta_value(proc.db)}",
            f"[bold]Command:[/bold] {_meta_value(proc.command)}",
            f"[bold]Time:[/bold] {_format_time_field(proc.time)}",
            f"[bold]State:[/bold] {_meta_value(proc.state)}",
            f"[bold]Program:[/bold] {_meta_value(proc.program)}",
        ]
        with Vertical(id="detail-container"):
            yield Static(f"Session {proc.id}", id="detail-title")
            yield Static("\n".join(meta_lines), id="detail-meta")
            query = (proc.info or "").strip()
            if query:
                yield Static(highlight_mysql(query), id="detail-body")
            else:
                yield Static("[dim]No active query.[/dim]", id="detail-body")

    def action_close(self) -> None:
        """Dismiss the modal."""
        self.dismiss(None)


class _TransactionDetailScreen(ModalScreen[None]):
    """Modal showing the full details of a transaction plus its query."""

    BINDINGS = [
        Binding("escape", "close", "Close", key_display="Esc"),
    ]

    CSS = """
    _TransactionDetailScreen {
        align: center middle;
        background: $background 80%;
    }

    #detail-container {
        width: 80%;
        max-width: 120;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    #detail-title {
        text-style: bold;
        padding-bottom: 1;
    }

    #detail-meta {
        height: auto;
        padding-bottom: 1;
    }

    .detail-section {
        text-style: bold;
        color: $accent;
        padding-top: 1;
    }

    .detail-sql {
        height: auto;
        padding: 0 0 1 1;
    }

    .detail-hist-label {
        color: $text-muted;
        padding-top: 1;
    }
    """

    def __init__(self, trx: TransactionRow) -> None:
        """Initialize with the transaction whose details are shown."""
        super().__init__()
        self._trx = trx

    def compose(self) -> ComposeResult:
        """Build the detail modal."""
        from mydba_tui.ui.mysql_highlight import highlight_mysql

        trx = self._trx
        meta_lines = [
            f"[bold]Trx ID:[/bold] {trx.trx_id}",
            f"[bold]Connection Id:[/bold] {trx.conn_id}",
            f"[bold]User:[/bold] {_meta_value(trx.user)}",
            f"[bold]Host:[/bold] {_meta_value(trx.host)}",
            f"[bold]DB:[/bold] {_meta_value(trx.db)}",
            f"[bold]State:[/bold] {_meta_value(trx.state)}",
            f"[bold]Started:[/bold] {_meta_value(trx.started)}",
            f"[bold]Age:[/bold] {_format_time_field(trx.age_seconds)}",
            f"[bold]Rows locked:[/bold] {trx.rows_locked} [dim](InnoDB estimate)[/dim]",
        ]
        with VerticalScroll(id="detail-container"):
            yield Static(f"Transaction {trx.trx_id}", id="detail-title")
            yield Static("\n".join(meta_lines), id="detail-meta")

            query = (trx.query or "").strip()
            yield Static("[bold]Current statement[/bold]", classes="detail-section")
            if query:
                yield Static(highlight_mysql(query), classes="detail-sql")
            else:
                yield Static("[dim]None (idle in transaction).[/dim]", classes="detail-sql")

            yield Static("[bold]Statement history[/bold]", classes="detail-section")
            yield _render_statement_history(self._load_history())

    def _load_history(self) -> list[StatementHistoryEntry] | None:
        """Load statement history for the transaction's connection.

        Returns None if not connected (so the modal can show an 'unavailable'
        note), otherwise the (possibly empty) list of recent statements.
        """
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            return None
        return fetch_statement_history(conn_result.connection, self._trx.conn_id)

    def action_close(self) -> None:
        """Dismiss the modal."""
        self.dismiss(None)


class _LockDetailScreen(ModalScreen[None]):
    """Modal showing a lock wait: the blocked and blocking sessions in full."""

    BINDINGS = [
        Binding("escape", "close", "Close", key_display="Esc"),
    ]

    CSS = """
    _LockDetailScreen {
        align: center middle;
        background: $background 80%;
    }

    #detail-container {
        width: 80%;
        max-width: 120;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    #detail-title {
        text-style: bold;
        padding-bottom: 1;
    }

    .detail-section {
        text-style: bold;
        color: $accent;
        padding-top: 1;
    }

    .detail-sql {
        height: auto;
        padding: 0 0 1 1;
    }

    .detail-hist-label {
        color: $text-muted;
        padding-top: 1;
    }

    #detail-meta {
        height: auto;
        padding-bottom: 1;
    }
    """

    def __init__(self, lock: LockWait) -> None:
        """Initialize with the lock wait whose detail is shown."""
        super().__init__()
        self._lock = lock

    def compose(self) -> ComposeResult:
        """Build the lock-wait detail modal."""
        from mydba_tui.ui.mysql_highlight import highlight_mysql

        lw = self._lock
        table = f"{lw.locked_schema}.{lw.locked_table}".strip(".")
        meta = [
            f"[bold]Locked table:[/bold] {_meta_value(table)}",
            f"[bold]Lock type:[/bold] {_meta_value(lw.locked_type)}",
            f"[bold]Wait age:[/bold] {_format_time_field(lw.wait_age_secs)}",
        ]
        with VerticalScroll(id="detail-container"):
            yield Static("Lock wait", id="detail-title")
            yield Static("\n".join(meta), id="detail-meta")

            yield Static(
                f"[bold]Waiting[/bold] — session {lw.waiting_pid} "
                f"(user {_meta_value(lw.waiting_user)}, "
                f"mode {_explain_mode(lw.waiting_lock_mode)})",
                classes="detail-section",
            )
            waiting = (lw.waiting_query or "").strip()
            yield Static(
                highlight_mysql(waiting) if waiting else "[dim]None.[/dim]",
                classes="detail-sql",
            )

            yield Static(
                f"[bold]Blocking[/bold] — session {lw.blocking_pid} "
                f"(user {_meta_value(lw.blocking_user)}, "
                f"mode {_explain_mode(lw.blocking_lock_mode)})",
                classes="detail-section",
            )
            blocking = (lw.blocking_query or "").strip()
            yield Static(
                highlight_mysql(blocking)
                if blocking
                else "[dim]None (blocking session is idle).[/dim]",
                classes="detail-sql",
            )

            # Statement history for the blocking session — helps when the
            # blocker is idle in transaction (no current query).
            yield Static(
                "[bold]Blocking session statement history[/bold]",
                classes="detail-section",
            )
            yield _render_statement_history(self._load_blocking_history())

    def _load_blocking_history(self) -> list[StatementHistoryEntry] | None:
        """Load statement history for the blocking session.

        Returns None if not connected (so the modal shows an 'unavailable'
        note), otherwise the (possibly empty) list of recent statements.
        """
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            return None
        return fetch_statement_history(conn_result.connection, self._lock.blocking_pid)

    def action_close(self) -> None:
        """Dismiss the modal."""
        self.dismiss(None)


class _MetadataLockDetailScreen(ModalScreen[None]):
    """Modal showing a metadata-lock wait: waiting/blocking sessions in full."""

    BINDINGS = [
        Binding("escape", "close", "Close", key_display="Esc"),
    ]

    CSS = """
    _MetadataLockDetailScreen {
        align: center middle;
        background: $background 80%;
    }

    #detail-container {
        width: 80%;
        max-width: 120;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    #detail-title {
        text-style: bold;
        padding-bottom: 1;
    }

    .detail-section {
        text-style: bold;
        color: $accent;
        padding-top: 1;
    }

    .detail-sql {
        height: auto;
        padding: 0 0 1 1;
    }

    #detail-meta {
        height: auto;
        padding-bottom: 1;
    }
    """

    def __init__(self, mdl: MetadataLockWait) -> None:
        """Initialize with the metadata-lock wait whose detail is shown."""
        super().__init__()
        self._mdl = mdl

    def compose(self) -> ComposeResult:
        """Build the metadata-lock detail modal."""
        from mydba_tui.ui.mysql_highlight import highlight_mysql

        m = self._mdl
        obj = f"{m.object_schema}.{m.object_name}".strip(".")
        meta = [
            f"[bold]Object:[/bold] {_meta_value(obj)}",
            f"[bold]Wait age:[/bold] {_format_time_field(m.wait_age_secs)}",
        ]
        with VerticalScroll(id="detail-container"):
            yield Static("Metadata lock wait", id="detail-title")
            yield Static("\n".join(meta), id="detail-meta")

            yield Static(
                f"[bold]Waiting[/bold] — session {m.waiting_pid} "
                f"({_meta_value(m.waiting_account)}, "
                f"lock {_explain_mode(m.waiting_lock_type)})",
                classes="detail-section",
            )
            waiting = (m.waiting_query or "").strip()
            yield Static(
                highlight_mysql(waiting) if waiting else "[dim]None.[/dim]",
                classes="detail-sql",
            )

            yield Static(
                f"[bold]Blocking[/bold] — session {m.blocking_pid} "
                f"({_meta_value(m.blocking_account)}, "
                f"lock {_explain_mode(m.blocking_lock_type)})",
                classes="detail-section",
            )

            # The MDL view has no blocking query; statement history is the way
            # to see what the (usually idle) blocker did to hold the lock.
            yield Static(
                "[bold]Blocking session statement history[/bold]",
                classes="detail-section",
            )
            yield _render_statement_history(self._load_blocking_history())

    def _load_blocking_history(self) -> list[StatementHistoryEntry] | None:
        """Load statement history for the blocking session.

        Returns None if not connected (so the modal shows an 'unavailable'
        note), otherwise the (possibly empty) list of recent statements.
        """
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            return None
        return fetch_statement_history(conn_result.connection, self._mdl.blocking_pid)

    def action_close(self) -> None:
        """Dismiss the modal."""
        self.dismiss(None)


class _UserDetailScreen(ModalScreen[None]):
    """Modal showing an account's summary plus its grants (fetched on demand)."""

    BINDINGS = [
        Binding("escape", "close", "Close", key_display="Esc"),
    ]

    CSS = """
    _UserDetailScreen {
        align: center middle;
        background: $background 80%;
    }

    #detail-container {
        width: 80%;
        max-width: 120;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    #detail-title {
        text-style: bold;
        padding-bottom: 1;
    }

    #detail-meta {
        height: auto;
        padding-bottom: 1;
    }

    .detail-section {
        text-style: bold;
        color: $accent;
        padding-top: 1;
    }

    .detail-sql {
        height: auto;
        padding: 0 0 1 1;
    }
    """

    def __init__(self, account: UserAccount) -> None:
        """Initialize with the account whose detail is shown."""
        super().__init__()
        self._account = account

    def compose(self) -> ComposeResult:
        """Build the account detail modal."""
        from mydba_tui.ui.mysql_highlight import highlight_mysql

        acc = self._account
        meta = [
            f"[bold]Group:[/bold] {_meta_value(acc.group)}",
            f"[bold]User:[/bold] {_meta_value(acc.user)}",
            f"[bold]Host:[/bold] {_meta_value(acc.host)}",
            f"[bold]Locked:[/bold] {'yes' if acc.locked else 'no'}",
            f"[bold]Password expired:[/bold] {'yes' if acc.password_expired else 'no'}",
            f"[bold]Password last changed:[/bold] {_meta_value(acc.password_last_changed)}",
            f"[bold]Auth plugin:[/bold] {_meta_value(acc.plugin)}",
        ]
        with VerticalScroll(id="detail-container"):
            yield Static(f"{acc.user}@{acc.host}", id="detail-title")
            yield Static("\n".join(meta), id="detail-meta")
            yield Static("[bold]Grants[/bold]", classes="detail-section")
            grants = self._load_grants()
            if grants is None:
                yield Static(
                    "[dim]Unable to read grants for this account.[/dim]",
                    classes="detail-sql",
                )
            elif not grants:
                yield Static("[dim]No grants.[/dim]", classes="detail-sql")
            else:
                for grant in grants:
                    yield Static(highlight_mysql(grant), classes="detail-sql")

    def _load_grants(self) -> list[str] | None:
        """Fetch the account's grants on demand.

        Returns None if not connected; otherwise the (possibly empty) grants.
        """
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.services.users import fetch_user_grants

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            return None
        return fetch_user_grants(conn_result.connection, self._account.user, self._account.host)

    def action_close(self) -> None:
        """Dismiss the modal."""
        self.dismiss(None)


class _KeyValueDetailScreen(ModalScreen[None]):
    """Modal showing a single key/value entry's full name and value."""

    BINDINGS = [
        Binding("escape", "close", "Close", key_display="Esc"),
    ]

    CSS = """
    _KeyValueDetailScreen {
        align: center middle;
        background: $background 80%;
    }

    #var-detail-container {
        width: 80%;
        max-width: 120;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    #var-detail-title {
        text-style: bold;
        padding-bottom: 1;
    }

    #var-detail-body {
        height: auto;
        max-height: 28;
        overflow-y: auto;
    }
    """

    def __init__(self, name: str, value: str) -> None:
        """Initialize with the variable name and value."""
        super().__init__()
        self._var_name: str = name
        self._var_value: str = value

    def compose(self) -> ComposeResult:
        """Build the variable detail modal."""
        with Vertical(id="var-detail-container"):
            yield Static(self._var_name, id="var-detail-title")
            body: str = self._var_value or "(empty)"
            yield Static(body, id="var-detail-body")

    def action_close(self) -> None:
        """Dismiss the modal."""
        self.dismiss(None)


# --- Performance (sys schema diagnostics) ---

# Max characters shown for a cell inline in a performance grid; the full value
# is available in the row detail.
_PERF_CELL_TRUNCATE = 60


class PerfGridView(LiveTableView):
    """Base for a sys-schema summary grid (Performance sub-tabs).

    Renders any sys view as a generic, dynamically-columned grid on top of the
    LiveTableView machinery (load-once, opt-in live with ``L``, interval ``I``,
    manual ``R``, filter ``/``). Each row is a list of display strings aligned
    to ``self._grid.columns``; ``Enter`` opens a per-family drill-down detail.

    Subclasses set ``id_prefix``/``noun`` and implement ``_fetch_grid`` (the
    summary view) and, optionally, ``_open_detail`` (the drill-down).
    """

    # Columns are discovered from the view result at runtime, so the fixed
    # LiveTableView column list is empty.
    columns: tuple[str, ...] = ()
    filter_placeholder = "Filter — Enter to keep, Esc to clear"

    def __init__(self) -> None:
        """Initialize perf grid state."""
        super().__init__()
        self._grid: GridData = GridData(columns=[], rows=[])
        self._table_columns: list[str] = []

    # --- Subclass hooks ---

    def _fetch_grid(self, connection: object) -> GridData:
        """Return the summary GridData. Subclasses implement."""
        raise NotImplementedError

    def _open_detail(self, row: dict[str, str]) -> None:
        """Open the drill-down detail for a row. Subclasses may override."""

    # --- LiveTableView plumbing ---

    def on_mount(self) -> None:
        """No auto-load on mount — the parent Performance tab drives loading.

        Loading a hidden sub-tab's (potentially heavy) sys view when the screen
        first mounts would be wasteful, so ``PerformanceView`` calls
        ``refresh_data`` on the active sub-tab only when the Performance tab is
        shown. Columns are added after the first fetch (they are dynamic).
        """

    def _fetch(self) -> list[object]:
        conn_result = self.app.db_connection  # type: ignore[attr-defined]
        grid = self._fetch_grid(conn_result.connection)
        self._grid = grid
        # Each "item" is a row; index carries the row so _row_dict can rebuild.
        return list(grid.rows)

    def _row_key(self, item: object) -> str:
        # A row's identity is its full contents — stable enough for cursor
        # preservation across refreshes without a natural primary key.
        row: list[str] = item  # type: ignore[assignment]
        return "\x00".join(row)

    def _row_cells(self, item: object) -> list[Text]:
        from mydba_tui.renderers.table import styled_cell

        row: list[str] = item  # type: ignore[assignment]
        cells: list[Text] = []
        for value in row:
            text = value if len(value) <= _PERF_CELL_TRUNCATE else value[:_PERF_CELL_TRUNCATE] + "…"
            cells.append(styled_cell(text))
        return cells

    def _matches(self, item: object, needle: str) -> bool:
        row: list[str] = item  # type: ignore[assignment]
        return needle in " ".join(row).lower()

    def _render_table(self, items: list[object]) -> None:
        """Rebuild dynamic columns when they change, then render rows."""
        table = self.query_one(f"#{self._table_id}", DataTable)
        if self._grid.columns != self._table_columns:
            table.clear(columns=True)
            for col in self._grid.columns:
                table.add_column(col, key=col)
            self._table_columns = list(self._grid.columns)
        super()._render_table(items)

    def _update_info(self, shown: int, total: int) -> None:
        """Info line; note when the source view is unavailable."""
        if not self._grid.available:
            self._show_message(
                "[yellow]Unavailable — this view needs the sys schema and "
                "performance_schema (absent on MariaDB or when disabled).[/yellow]"
            )
            return
        super()._update_info(shown, total)

    def _row_dict(self, item: object) -> dict[str, str]:
        """Map a row to a {column: value} dict using the grid's headers."""
        row: list[str] = item  # type: ignore[assignment]
        return dict(zip(self._grid.columns, row, strict=False))

    def action_show_detail(self) -> None:
        """Open the drill-down detail for the selected row."""
        item = self._selected_item()
        if item is None:
            self.notify("No row selected.", severity="warning")
            return
        self._open_detail(self._row_dict(item))


class TopQueriesView(PerfGridView):
    """Top Queries — normalized statement digests by total latency."""

    BINDINGS = [
        *LiveTableView.LIVE_BINDINGS,
        Binding("w", "open_in_workspace", "To Workspace", key_display="W"),
    ]

    id_prefix = "perf-stmts"
    noun = "statements"
    filter_placeholder = "Filter (query, db) — Enter to keep, Esc to clear"

    def _fetch_grid(self, connection: object) -> GridData:
        return fetch_view(
            connection,  # type: ignore[arg-type]
            "admin/perf/statement_analysis.sql",
            "administration.performance.statements",
        )

    def _open_detail(self, row: dict[str, str]) -> None:
        digest = row.get("digest", "")
        self.app.push_screen(_StatementDetailScreen(digest, row.get("query", "")))

    def action_open_in_workspace(self) -> None:
        """Open the selected statement's sample/normalized text in the Workspace."""
        item = self._selected_item()
        if item is None:
            self.notify("No row selected.", severity="warning")
            return
        row = self._row_dict(item)
        digest = row.get("digest", "")

        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        text = row.get("query", "")
        if digest and isinstance(conn_result, ConnectionResult):
            sample = fetch_statement_digest_sample(conn_result.connection, digest)
            if sample is not None:
                text = sample.sample_text or sample.digest_text or text

        if not text.strip():
            self.notify("No statement text available.", severity="information")
            return
        snippet = "-- Statement from Performance → Top Queries\n" + text
        try:
            workspace = self.app.get_screen("workspace", WorkspaceScreen)
        except Exception:
            self.notify("SQL Workspace unavailable.", severity="error")
            return
        workspace.load_query(snippet)
        self.app.push_screen("workspace")


class _StatementDetailScreen(ModalScreen[None]):
    """Modal showing a statement digest's full normalized text and a sample."""

    BINDINGS = [
        Binding("escape", "close", "Close", key_display="Esc"),
    ]

    CSS = """
    _StatementDetailScreen {
        align: center middle;
        background: $background 80%;
    }

    #detail-container {
        width: 85%;
        max-width: 130;
        height: auto;
        max-height: 85%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    #detail-title {
        text-style: bold;
        padding-bottom: 1;
    }

    .detail-section {
        text-style: bold;
        color: $accent;
        padding-top: 1;
    }

    .detail-sql {
        height: auto;
        padding: 0 0 1 1;
    }
    """

    def __init__(self, digest: str, fallback_query: str) -> None:
        """Initialize with the digest and the grid's (truncated) query text."""
        super().__init__()
        self._digest = digest
        self._fallback_query = fallback_query

    def compose(self) -> ComposeResult:
        """Build the statement detail modal."""
        from mydba_tui.ui.mysql_highlight import highlight_mysql

        sample = self._load_sample()
        with VerticalScroll(id="detail-container"):
            yield Static("Statement digest", id="detail-title")
            if sample is None:
                meta = f"[bold]Digest:[/bold] {_meta_value(self._digest)}"
                yield Static(meta, classes="detail-sql")
                yield Static("[bold]Normalized[/bold]", classes="detail-section")
                yield Static(highlight_mysql(self._fallback_query or "—"), classes="detail-sql")
                return
            meta_lines = [
                f"[bold]Digest:[/bold] {_meta_value(self._digest)}",
                f"[bold]Schema:[/bold] {_meta_value(sample.schema_name)}",
                f"[bold]Executions:[/bold] {_meta_value(sample.exec_count)}",
                f"[bold]First seen:[/bold] {_meta_value(sample.first_seen)}",
                f"[bold]Last seen:[/bold] {_meta_value(sample.last_seen)}",
            ]
            yield Static("\n".join(meta_lines), classes="detail-sql")
            yield Static("[bold]Normalized statement[/bold]", classes="detail-section")
            yield Static(
                highlight_mysql(sample.digest_text or self._fallback_query or "—"),
                classes="detail-sql",
            )
            yield Static("[bold]Sample statement[/bold]", classes="detail-section")
            if sample.sample_text.strip():
                yield Static(highlight_mysql(sample.sample_text), classes="detail-sql")
            else:
                yield Static("[dim]No sample captured.[/dim]", classes="detail-sql")

    def _load_sample(self) -> StatementDigestSample | None:
        """Fetch the digest's full text and sample on demand (best-effort)."""
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if not self._digest or not isinstance(conn_result, ConnectionResult):
            return None
        return fetch_statement_digest_sample(conn_result.connection, self._digest)

    def action_close(self) -> None:
        """Dismiss the modal."""
        self.dismiss(None)


@dataclass(frozen=True)
class _BreakdownSpec:
    """One drill-down breakdown view shown as a sub-tab in a detail modal.

    Attributes:
        label: Sub-tab title.
        sql_file: Breakdown query file (``sql/…``). When ``keyed`` is True it has
            a single ``%s`` marker bound to the selected row's key.
        source: SQL-log source label.
        keyed: When True (default) the query is parameterized by the row key;
            when False it is a global view shown as related context (e.g. the
            I/O family, whose breakdowns are server-global, not per-file).
    """

    label: str
    sql_file: str
    source: str
    keyed: bool = True


def _render_grid_table(grid: GridData) -> Static:
    """Render a GridData as an aligned Rich table inside a Static.

    Used inside detail modals so a breakdown view is shown compactly without a
    full DataTable widget. Explains empty/unavailable results.
    """
    from rich.table import Table

    if not grid.available:
        return Static(
            "[dim]Unavailable — needs the sys schema and performance_schema.[/dim]",
            classes="detail-sql",
        )
    if grid.empty:
        return Static("[dim]No data.[/dim]", classes="detail-sql")

    table: Table = Table(expand=True, show_edge=False, pad_edge=False)
    for col in grid.columns:
        table.add_column(col, overflow="fold")
    for row in grid.rows:
        table.add_row(*row)
    return Static(table, classes="detail-sql")


class _BreakdownDetailScreen(ModalScreen[None]):
    """Generic drill-down modal: breakdown views as sub-tabs, keyed to a row.

    Given a subject key (e.g. a user or host) and a list of breakdown specs,
    each breakdown is fetched on demand (best-effort, parameterized by the key)
    and shown in its own sub-tab. Reused by the Performance families that follow
    the sys-schema "summary + _by_* breakdowns" pattern.
    """

    BINDINGS = [
        Binding("escape", "close", "Close", key_display="Esc"),
    ]

    CSS = """
    _BreakdownDetailScreen {
        align: center middle;
        background: $background 80%;
    }

    #detail-container {
        width: 85%;
        max-width: 140;
        height: 80%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    #detail-title {
        text-style: bold;
        padding-bottom: 1;
    }

    #detail-tabs {
        height: 1fr;
    }

    .detail-sql {
        height: auto;
        padding: 0 0 1 0;
    }
    """

    def __init__(self, title: str, params: tuple[str, ...], specs: list[_BreakdownSpec]) -> None:
        """Initialize with the modal title, the drill-down params, and specs.

        ``params`` are bound (in order) to the ``%s`` markers of each keyed
        breakdown — one value for a single-key family (user/host/event), or
        several for a composite key (e.g. schema + table).
        """
        super().__init__()
        self._title = title
        self._params = params
        self._specs = specs

    def compose(self) -> ComposeResult:
        """Build the detail modal with one sub-tab per breakdown."""
        with Vertical(id="detail-container"):
            yield Static(self._title, id="detail-title")
            with TabbedContent(id="detail-tabs"):
                for i, spec in enumerate(self._specs):
                    with TabPane(spec.label, id=f"detail-bd-{i}"):
                        yield _render_grid_table(self._fetch(spec))

    def _fetch(self, spec: _BreakdownSpec) -> GridData:
        """Run one breakdown (keyed to the subject) or global context view."""
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if not isinstance(conn_result, ConnectionResult):
            return GridData(columns=[], rows=[], available=False)
        if spec.keyed:
            return fetch_breakdown(conn_result.connection, spec.sql_file, self._params, spec.source)
        return fetch_view(conn_result.connection, spec.sql_file, spec.source)

    def action_close(self) -> None:
        """Dismiss the modal."""
        self.dismiss(None)


class UsersPerfView(PerfGridView):
    """Performance > Users — per-user activity summary with drill-down."""

    BINDINGS = [*LiveTableView.LIVE_BINDINGS]

    id_prefix = "perf-users"
    noun = "users"
    filter_placeholder = "Filter (user) — Enter to keep, Esc to clear"

    _BREAKDOWNS = [
        _BreakdownSpec(
            "Statement Latency",
            "admin/perf/user_summary_by_statement_latency.sql",
            "administration.performance.user.statement_latency",
        ),
        _BreakdownSpec(
            "Statement Types",
            "admin/perf/user_summary_by_statement_type.sql",
            "administration.performance.user.statement_type",
        ),
        _BreakdownSpec(
            "Stages",
            "admin/perf/user_summary_by_stages.sql",
            "administration.performance.user.stages",
        ),
        _BreakdownSpec(
            "File I/O",
            "admin/perf/user_summary_by_file_io.sql",
            "administration.performance.user.file_io",
        ),
        _BreakdownSpec(
            "File I/O Types",
            "admin/perf/user_summary_by_file_io_type.sql",
            "administration.performance.user.file_io_type",
        ),
    ]

    def _fetch_grid(self, connection: object) -> GridData:
        return fetch_view(
            connection,  # type: ignore[arg-type]
            "admin/perf/user_summary.sql",
            "administration.performance.users",
        )

    def _open_detail(self, row: dict[str, str]) -> None:
        user = row.get("user", "")
        if not user:
            self.notify("No user for this row.", severity="warning")
            return
        self.app.push_screen(_BreakdownDetailScreen(f"User: {user}", (user,), self._BREAKDOWNS))


class HostsPerfView(PerfGridView):
    """Performance > Hosts — per-host activity summary with drill-down."""

    BINDINGS = [*LiveTableView.LIVE_BINDINGS]

    id_prefix = "perf-hosts"
    noun = "hosts"
    filter_placeholder = "Filter (host) — Enter to keep, Esc to clear"

    _BREAKDOWNS = [
        _BreakdownSpec(
            "Statement Latency",
            "admin/perf/host_summary_by_statement_latency.sql",
            "administration.performance.host.statement_latency",
        ),
        _BreakdownSpec(
            "Statement Types",
            "admin/perf/host_summary_by_statement_type.sql",
            "administration.performance.host.statement_type",
        ),
        _BreakdownSpec(
            "Stages",
            "admin/perf/host_summary_by_stages.sql",
            "administration.performance.host.stages",
        ),
        _BreakdownSpec(
            "File I/O",
            "admin/perf/host_summary_by_file_io.sql",
            "administration.performance.host.file_io",
        ),
        _BreakdownSpec(
            "File I/O Types",
            "admin/perf/host_summary_by_file_io_type.sql",
            "administration.performance.host.file_io_type",
        ),
    ]

    def _fetch_grid(self, connection: object) -> GridData:
        return fetch_view(
            connection,  # type: ignore[arg-type]
            "admin/perf/host_summary.sql",
            "administration.performance.hosts",
        )

    def _open_detail(self, row: dict[str, str]) -> None:
        host = row.get("host", "")
        if not host:
            self.notify("No host for this row.", severity="warning")
            return
        self.app.push_screen(_BreakdownDetailScreen(f"Host: {host}", (host,), self._BREAKDOWNS))


class WaitsPerfView(PerfGridView):
    """Performance > Waits — global wait events with per-user/host drill-down."""

    BINDINGS = [*LiveTableView.LIVE_BINDINGS]

    id_prefix = "perf-waits"
    noun = "wait events"
    filter_placeholder = "Filter (event) — Enter to keep, Esc to clear"

    _BREAKDOWNS = [
        _BreakdownSpec(
            "By User",
            "admin/perf/waits_by_user_by_latency.sql",
            "administration.performance.wait.by_user",
        ),
        _BreakdownSpec(
            "By Host",
            "admin/perf/waits_by_host_by_latency.sql",
            "administration.performance.wait.by_host",
        ),
    ]

    def _fetch_grid(self, connection: object) -> GridData:
        return fetch_view(
            connection,  # type: ignore[arg-type]
            "admin/perf/waits_global_by_latency.sql",
            "administration.performance.waits",
        )

    def _open_detail(self, row: dict[str, str]) -> None:
        # The global view names the column `events`; the breakdowns key on it
        # as `event`.
        event = row.get("events", "")
        if not event:
            self.notify("No wait event for this row.", severity="warning")
            return
        self.app.push_screen(_BreakdownDetailScreen(f"Wait: {event}", (event,), self._BREAKDOWNS))


class IoPerfView(PerfGridView):
    """Performance > I/O — file I/O hotspots with global I/O context."""

    BINDINGS = [*LiveTableView.LIVE_BINDINGS]

    id_prefix = "perf-io"
    noun = "files"
    filter_placeholder = "Filter (file) — Enter to keep, Esc to clear"

    # These breakdowns are server-global (not per-file), shown as related I/O
    # context alongside the selected file.
    _BREAKDOWNS = [
        _BreakdownSpec(
            "I/O by Wait Type",
            "admin/perf/io_global_by_wait_by_latency.sql",
            "administration.performance.io.by_wait",
            keyed=False,
        ),
        _BreakdownSpec(
            "I/O by Thread",
            "admin/perf/io_by_thread_by_latency.sql",
            "administration.performance.io.by_thread",
            keyed=False,
        ),
    ]

    def _fetch_grid(self, connection: object) -> GridData:
        return fetch_view(
            connection,  # type: ignore[arg-type]
            "admin/perf/io_global_by_file_by_bytes.sql",
            "administration.performance.io",
        )

    def _open_detail(self, row: dict[str, str]) -> None:
        file = row.get("file", "")
        title = f"I/O: {file}" if file else "I/O context"
        # Global context breakdowns; params unused (keyed=False).
        self.app.push_screen(_BreakdownDetailScreen(title, (), self._BREAKDOWNS))


class TablesPerfView(PerfGridView):
    """Performance > Tables — per-table access stats with index/buffer drill-down."""

    BINDINGS = [*LiveTableView.LIVE_BINDINGS]

    id_prefix = "perf-tables"
    noun = "tables"
    filter_placeholder = "Filter (schema, table) — Enter to keep, Esc to clear"

    _BREAKDOWNS = [
        _BreakdownSpec(
            "Indexes",
            "admin/perf/schema_index_statistics.sql",
            "administration.performance.table.indexes",
        ),
        _BreakdownSpec(
            "Buffer Pool",
            "admin/perf/schema_table_statistics_with_buffer.sql",
            "administration.performance.table.buffer",
        ),
    ]

    def _fetch_grid(self, connection: object) -> GridData:
        return fetch_view(
            connection,  # type: ignore[arg-type]
            "admin/perf/schema_table_statistics.sql",
            "administration.performance.tables",
        )

    def _open_detail(self, row: dict[str, str]) -> None:
        schema = row.get("table_schema", "")
        table = row.get("table_name", "")
        if not schema or not table:
            self.notify("No table for this row.", severity="warning")
            return
        self.app.push_screen(
            _BreakdownDetailScreen(f"{schema}.{table}", (schema, table), self._BREAKDOWNS)
        )


class IndexesPerfView(PerfGridView):
    """Performance > Indexes — unused indexes, with redundant indexes as context."""

    BINDINGS = [*LiveTableView.LIVE_BINDINGS]

    id_prefix = "perf-indexes"
    noun = "unused indexes"
    filter_placeholder = "Filter (schema, table, index) — Enter to keep, Esc to clear"

    _BREAKDOWNS = [
        _BreakdownSpec(
            "Redundant Indexes",
            "admin/perf/schema_redundant_indexes.sql",
            "administration.performance.index.redundant",
            keyed=False,
        ),
    ]

    def _fetch_grid(self, connection: object) -> GridData:
        return fetch_view(
            connection,  # type: ignore[arg-type]
            "admin/perf/schema_unused_indexes.sql",
            "administration.performance.indexes",
        )

    def _open_detail(self, row: dict[str, str]) -> None:
        # Redundant indexes is a server-global list (with DROP statements),
        # shown as related index-housekeeping context.
        self.app.push_screen(_BreakdownDetailScreen("Redundant Indexes", (), self._BREAKDOWNS))


class FullScansView(TopQueriesView):
    """Performance > Full Scans — statements that scanned tables without an index.

    Shares Top Queries' digest drill-down (full text + sample, open in
    Workspace); only the summary view differs.
    """

    id_prefix = "perf-fullscans"
    noun = "statements"
    filter_placeholder = "Filter (query, db) — Enter to keep, Esc to clear"

    def _fetch_grid(self, connection: object) -> GridData:
        return fetch_view(
            connection,  # type: ignore[arg-type]
            "admin/perf/statements_with_full_table_scans.sql",
            "administration.performance.full_scans",
        )


class MemoryPerfView(PerfGridView):
    """Performance > Memory — current memory by allocation type, with context."""

    BINDINGS = [*LiveTableView.LIVE_BINDINGS]

    id_prefix = "perf-memory"
    noun = "allocation types"
    filter_placeholder = "Filter (event) — Enter to keep, Esc to clear"

    # Global context breakdowns (not per-event): who holds memory right now.
    _BREAKDOWNS = [
        _BreakdownSpec(
            "By User",
            "admin/perf/memory_by_user_by_current_bytes.sql",
            "administration.performance.memory.by_user",
            keyed=False,
        ),
        _BreakdownSpec(
            "By Thread",
            "admin/perf/memory_by_thread_by_current_bytes.sql",
            "administration.performance.memory.by_thread",
            keyed=False,
        ),
    ]

    def _fetch_grid(self, connection: object) -> GridData:
        return fetch_view(
            connection,  # type: ignore[arg-type]
            "admin/perf/memory_global_by_current_bytes.sql",
            "administration.performance.memory",
        )

    def _open_detail(self, row: dict[str, str]) -> None:
        event = row.get("event_name", "")
        title = f"Memory: {event}" if event else "Memory context"
        self.app.push_screen(_BreakdownDetailScreen(title, (), self._BREAKDOWNS))


class PerformanceView(Vertical):
    """Performance — sys-schema diagnostics, organized as a family of sub-tabs.

    Each sub-tab is a summary grid whose rows drill down into keyed breakdown
    views. Read-only; the sys schema and performance_schema must be available
    (absent/limited on MariaDB), and unavailable sub-tabs show a note.
    """

    DEFAULT_CSS = """
    PerformanceView {
        height: 1fr;
    }

    PerformanceView TabPane {
        padding: 0;
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        """Build the Performance sub-tab layout."""
        with TabbedContent(id="perf-tabs"):
            with TabPane("Top Queries", id="perf-tab-topqueries"):
                yield TopQueriesView()
            with TabPane("Users", id="perf-tab-users"):
                yield UsersPerfView()
            with TabPane("Hosts", id="perf-tab-hosts"):
                yield HostsPerfView()
            with TabPane("Waits", id="perf-tab-waits"):
                yield WaitsPerfView()
            with TabPane("I/O", id="perf-tab-io"):
                yield IoPerfView()
            with TabPane("Tables", id="perf-tab-tables"):
                yield TablesPerfView()
            with TabPane("Indexes", id="perf-tab-indexes"):
                yield IndexesPerfView()
            with TabPane("Full Scans", id="perf-tab-fullscans"):
                yield FullScansView()
            with TabPane("Memory", id="perf-tab-memory"):
                yield MemoryPerfView()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Load the newly activated sub-tab's grid, but only while visible.

        This fires during initial mount too (for the default sub-tab); loading
        then would query for a hidden tab, so we only act when the Performance
        tab is the active Administration tab.
        """
        event.stop()
        if not _view_is_active_tab(self):
            return
        pane = event.tabbed_content.get_pane(event.tab)
        if pane is None:
            return
        for live in pane.walk_children(LiveTableView):
            live.refresh_data()

    def refresh_data(self) -> None:
        """Load the currently active sub-tab when the Performance tab is shown."""
        try:
            tabs = self.query_one("#perf-tabs", TabbedContent)
        except Exception:
            return
        active = tabs.active_pane
        if active is None:
            return
        for live in active.walk_children(LiveTableView):
            live.refresh_data()


class AdministrationScreen(Screen[None]):
    """Administration — tabbed operational views (Process List, Variables, ...)."""

    BINDINGS = [
        Binding("escape", "go_back", "Back", key_display="Esc"),
        Binding("f10", "quit", "Exit", key_display="F10"),
    ]

    CSS = """
    AdministrationScreen {
        overflow: hidden;
    }

    AdministrationScreen #admin-tabs {
        height: 1fr;
    }

    AdministrationScreen Footer {
        dock: bottom;
    }

    AdministrationScreen TabPane {
        padding: 0;
        height: 1fr;
        overflow: hidden;
    }
    """

    def compose(self) -> ComposeResult:
        """Build the tabbed administration layout."""
        yield Header()
        yield StatusBar(id="status-bar")
        with TabbedContent(id="admin-tabs"):
            with TabPane("Process List", id="tab-processlist"):
                yield ProcessListView()
            with TabPane("Connections", id="tab-connections"):
                yield ConnectionsView()
            with TabPane("Transactions", id="tab-transactions"):
                yield TransactionsView()
            with TabPane("InnoDB Locks", id="tab-locks"):
                yield LocksView()
            with TabPane("Metadata Locks", id="tab-metadata-locks"):
                yield MetadataLocksView()
            with TabPane("Users", id="tab-users"):
                yield UsersView()
            with TabPane("Variables", id="tab-variables"):
                yield VariablesView()
            with TabPane("Status", id="tab-status"):
                yield StatusView()
            with TabPane("Replication", id="tab-replication"):
                yield ReplicationView()
            with TabPane("Performance", id="tab-performance"):
                yield PerformanceView()
        yield Footer()

    def on_mount(self) -> None:
        """Sync the status bar on mount."""
        self._sync_status_bar()

    def on_screen_resume(self) -> None:
        """Sync status and refresh the active tab when returning."""
        self._sync_status_bar()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Refresh the newly activated tab's data (respects each view's policy)."""
        pane = event.tabbed_content.get_pane(event.tab)
        if pane is None:
            return
        # The Performance tab manages its own sub-tabs; refresh only its active
        # sub-tab (and don't also match its inner grids via walk_children).
        perf = list(pane.walk_children(PerformanceView))
        if perf:
            for pv in perf:
                pv.refresh_data()
            return
        for view in pane.walk_children(KeyValueView):
            view.refresh_data()
        for live in pane.walk_children(LiveTableView):
            live.refresh_data()
        for repl in pane.walk_children(ReplicationView):
            repl.refresh_data()
        # Focus is intentionally left on the tab bar so arrow keys switch tabs;
        # the user presses Tab to move focus into the active tab's content
        # (matching the Object Browser). This applies to the Replication tab
        # too — it is not focused automatically on open.

    def _sync_status_bar(self) -> None:
        """Sync the status bar with the current connection state."""
        status = getattr(self.app, "connection_status", "")
        if status:
            self.query_one("#status-bar", StatusBar).status_text = status

    def action_go_back(self) -> None:
        """Return to the object browser."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()
