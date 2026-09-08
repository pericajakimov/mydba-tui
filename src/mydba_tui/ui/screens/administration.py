"""
Administration screen.

Provides operational visibility for day-to-day administration. The first
section is the Process List: a live, filterable view of active MySQL sessions
with the ability to terminate a session or its running query.

All SQL executed here is written to the SQL log for transparency.
"""

from __future__ import annotations

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.timer import Timer
from textual.widgets import DataTable, Footer, Header, Input, Static, TabbedContent, TabPane

from mydba_tui.services.connections import ConnectionStat, fetch_connection_stats
from mydba_tui.services.processlist import (
    PROCESS_COLUMNS,
    ProcessRow,
    fetch_processes,
    kill_session,
)
from mydba_tui.services.status import fetch_status
from mydba_tui.services.transactions import (
    TRANSACTION_COLUMNS,
    StatementHistoryEntry,
    TransactionRow,
    fetch_statement_history,
    fetch_transactions,
)
from mydba_tui.services.variables import fetch_variables
from mydba_tui.ui.screens.workspace import WorkspaceScreen
from mydba_tui.ui.widgets import ConfirmDialog, StatusBar

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
        Binding("p", "toggle_pause", "Pause/Resume", key_display="P"),
        Binding("slash", "filter", "Filter", key_display="/"),
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
        dock: bottom;
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
        self._paused: bool = False
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
        """Set up the table columns and start auto-refresh."""
        table = self.query_one(f"#{self._table_id}", DataTable)
        for col in self.columns:
            table.add_column(col, key=col)

        self.action_refresh()

        interval = getattr(getattr(self.app, "settings", None), "refresh_interval", 3)
        interval = max(1, int(interval))
        self._refresh_timer = self.set_interval(interval, self._on_refresh_tick)

    def refresh_data(self) -> None:
        """Public hook to reload data (called when the tab is shown)."""
        self.action_refresh()

    # --- Data loading ---

    def _on_refresh_tick(self) -> None:
        """Timer callback — refresh unless paused and only when this tab is active.

        Background tabs must not query the shared connection; that both wastes
        the connection and slows the visible tab.
        """
        if self._paused or not _view_is_active_tab(self):
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
        if self._paused:
            flags.append("[yellow]PAUSED[/yellow]")
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

    def action_toggle_pause(self) -> None:
        """Toggle auto-refresh."""
        self._paused = not self._paused
        self._render_table(self._items)
        self.notify("Auto-refresh paused." if self._paused else "Auto-refresh resumed.")

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
        if self._paused:
            flags.append("[yellow]PAUSED[/yellow]")
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
        dock: bottom;
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
        self.action_refresh()

    def refresh_data(self) -> None:
        """Public hook to (re)load data when the tab is shown."""
        if self.load_once and self._rows:
            return
        self.action_refresh()

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
            history = self._load_history()
            if history is None:
                yield Static(
                    "[dim]Unavailable — requires performance_schema statement history.[/dim]",
                    classes="detail-sql",
                )
            elif not history:
                yield Static("[dim]No recent statements.[/dim]", classes="detail-sql")
            else:
                for i, entry in enumerate(history, 1):
                    ms = f"{entry.duration_ms:.1f} ms" if entry.duration_ms else ""
                    label = f"[dim]{i}.[/dim] [dim]{ms}[/dim]" if ms else f"[dim]{i}.[/dim]"
                    yield Static(label, classes="detail-hist-label")
                    yield Static(highlight_mysql(entry.sql), classes="detail-sql")

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


class AdministrationScreen(Screen[None]):
    """Administration — tabbed operational views (Process List, Variables, ...)."""

    BINDINGS = [
        Binding("escape", "go_back", "Back", key_display="Esc"),
        Binding("f10", "quit", "Exit", key_display="F10"),
    ]

    CSS = """
    AdministrationScreen TabPane {
        padding: 0;
        height: 1fr;
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
            with TabPane("Variables", id="tab-variables"):
                yield VariablesView()
            with TabPane("Status", id="tab-status"):
                yield StatusView()
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
        for view in pane.walk_children(KeyValueView):
            view.refresh_data()
        for live in pane.walk_children(LiveTableView):
            live.refresh_data()
        # Focus is intentionally left on the tab bar so arrow keys switch tabs;
        # the user presses Tab to move focus into the active tab's content
        # (matching the Object Browser).

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
