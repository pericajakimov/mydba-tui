"""
Monitoring screen.

A lightweight, live "what's happening right now" dashboard — deliberately not a
PMM/Grafana replacement. It presents a small, curated set of braille sparkline
graphs plus instant metrics, organized into sub-tabs (Overview, InnoDB,
Throughput & Traffic, Locks & Contention, and — on a replica — Replication).

Every metric comes from a single cheap ``SHOW GLOBAL STATUS`` snapshot per tick;
rates are computed as deltas between snapshots. Graphs keep only session-local
history and sample only while their tab is visible. Live updates are ON by
default (press ``L`` to pause, ``I`` to change the interval).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane

from mydba_tui.renderers.chart import render_timeseries
from mydba_tui.services.monitoring import Snapshot, fetch_snapshot, rate, sum_rate
from mydba_tui.ui.screens.administration import _current_interval, _cycle_interval
from mydba_tui.ui.widgets import StatusBar

# How much history the graphs keep, as a duration; the sample cap is derived
# from the refresh interval (matching the replication lag graph).
_HISTORY_SECONDS = 30 * 60


@dataclass
class _GraphSpec:
    """One graph in a sub-view.

    Attributes:
        key: Stable id (used for the widget id and the series store).
        title: Human title shown above the chart.
        value: Given (prev, cur) snapshots, returns the value to plot now.
        unit: Short unit label for the current/peak readout (e.g. "/s", "%").
        color: Chart line colour.
    """

    key: str
    title: str
    value: Callable[[Snapshot, Snapshot], float]
    unit: str = "/s"
    color: str = "cyan"


@dataclass
class _MetricSpec:
    """One instant metric in the strip.

    Attributes:
        label: Metric label.
        value: Given the current snapshot, returns the display string.
    """

    label: str
    value: Callable[[Snapshot], str]


def _fmt_num(n: float) -> str:
    """Format a rate/number compactly (e.g. 1.2k, 3.4M)."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    if n >= 100:
        return f"{n:.0f}"
    return f"{n:.1f}"


def _fmt_bytes(n: float) -> str:
    """Format a byte count as human-readable (KiB/MiB/GiB)."""
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{n:.0f} B"


def _fmt_conns(s: Snapshot) -> str:
    """Format 'connected / max' from a snapshot."""
    connected = int(s.gauge("Threads_connected"))
    maximum = int(s.var_float("max_connections"))
    return f"{connected} / {maximum}"


def _fmt_uptime(seconds: float) -> str:
    """Format an uptime in seconds as e.g. '12d 04h' or '3h 12m'."""
    secs = int(seconds)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours:02d}h"
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


class MetricGraph(Static):
    """A bordered graph box: a title, a current/peak readout, and a framed chart.

    Each graph lives in its own rounded box (the metric name is the box title)
    so several can be scanned and correlated at a glance. The chart spans a
    fixed time window and fills from the right (see render_timeseries).
    """

    DEFAULT_CSS = """
    MetricGraph {
        height: 100%;
        border: round $accent;
        border-title-color: $text;
        border-title-style: bold;
        padding: 0 1;
    }
    """

    def render_series(
        self,
        title: str,
        series: list[float],
        unit: str,
        color: str,
        interval: int,
        window_seconds: int,
    ) -> None:
        """Render the graph for a rolling series over a fixed time window."""
        self.border_title = title
        # Account for the border (2 cells each axis) plus the y-axis gutter.
        width = max(self.size.width - 2, 20)
        height = max(self.size.height - 4, 3)
        if not series:
            self.update(Text("collecting…", style="dim"))
            return
        current = series[-1]
        peak = max(series)
        head = Text()
        head.append(f"{_fmt_num(current)}{unit}", style=color)
        head.append(f"   peak {_fmt_num(peak)}{unit}", style="dim")
        head.append("\n")
        chart = render_timeseries(
            series,
            width,
            height,
            interval,
            window_seconds,
            unit=unit,
            color=color,
            y_max=max(peak, 1.0),
            value_fmt=_fmt_num,
        )
        self.update(head + chart)


class MonitoringSubView(Vertical):
    """Base for a Monitoring sub-tab: a 2x2 graph grid + an instant-metrics strip.

    Live updates are ON by default (unlike the Administration tabs) since this
    is a dashboard. The MonitoringScreen drives sampling for every sub-view on a
    single timer, so all sub-tabs keep collecting continuously even while
    hidden — switching sub-tabs never leaves a graph with a stale gap. History
    is session-local and rolling.
    """

    DEFAULT_CSS = """
    MonitoringSubView {
        height: 1fr;
    }

    MonitoringSubView .mon-graphs {
        grid-size: 2 2;
        grid-gutter: 1;
        height: 1fr;
        padding: 1 1 0 1;
    }

    MonitoringSubView .mon-metrics {
        height: auto;
        padding: 1 2;
        color: $text-muted;
        border-top: solid $panel;
    }
    """

    # Subclasses override.
    id_prefix: str = "mon"
    graphs: tuple[_GraphSpec, ...] = ()
    metrics: tuple[_MetricSpec, ...] = ()

    def __init__(self) -> None:
        """Initialize sub-view state."""
        super().__init__()
        self._live: bool = True  # dashboards start live
        self._interval: int = 5
        self._prev: Snapshot | None = None
        self._series: dict[str, list[float]] = {g.key: [] for g in self.graphs}
        self._last: Snapshot | None = None
        self._sample_cap: int = 360
        self._extra_metrics_cache: list[tuple[str, str]] = []

    def compose(self) -> ComposeResult:
        """Build the 2x2 graph grid and the metrics strip."""
        with Grid(classes="mon-graphs"):
            for spec in self.graphs:
                yield MetricGraph(id=f"{self.id_prefix}-{spec.key}")
        yield Static("", classes="mon-metrics", id=f"{self.id_prefix}-metrics")

    def set_context(self, interval: int, live: bool) -> None:
        """Push the screen-level live/interval state used for rendering.

        The MonitoringScreen owns the single timer and drives sampling for all
        sub-views (so every sub-tab's history stays continuous regardless of
        which one is visible); each view only needs the current interval (for
        the chart window) and live flag (for the status line).
        """
        self._interval = interval
        self._live = live
        self._sample_cap = max(_HISTORY_SECONDS // max(interval, 1), 2)

    def sample(self) -> None:
        """Public entry point: take one sample and re-render (driven by screen)."""
        self._sample()

    # --- Sampling ---

    def _sample(self) -> None:
        """Take a snapshot, update rolling series, and re-render."""
        from mydba_tui.connection import ConnectionResult

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self._render_metrics_message("[yellow]Not connected to a database.[/yellow]")
            return

        cur = fetch_snapshot(conn_result.connection)
        if not cur.available:
            self._render_metrics_message("[red]Could not read server status.[/red]")
            return

        # Rates need a previous snapshot; the first sample only seeds it.
        if self._prev is not None:
            for spec in self.graphs:
                value = spec.value(self._prev, cur)
                series = self._series[spec.key]
                series.append(value)
                if len(series) > self._sample_cap:
                    del series[: len(series) - self._sample_cap]
        self._prev = cur
        self._last = cur
        try:
            self._extra_metrics_cache = self._extra_metrics()
        except Exception:
            self._extra_metrics_cache = []
        self._render_all()

    # --- Rendering ---

    def _render_all(self) -> None:
        """Re-render all graphs and the metrics strip."""
        for spec in self.graphs:
            try:
                graph = self.query_one(f"#{self.id_prefix}-{spec.key}", MetricGraph)
            except Exception:
                continue
            graph.render_series(
                spec.title,
                self._series[spec.key],
                spec.unit,
                spec.color,
                self._interval,
                _HISTORY_SECONDS,
            )
        self._render_metrics()

    def _extra_metrics(self) -> list[tuple[str, str]]:
        """Optional extra (label, value) metrics that need a live query.

        Computed at sample time (with connection access) rather than from the
        status snapshot. Subclasses override; the default is none.
        """
        return []

    def _render_metrics(self) -> None:
        """Render the instant-metrics strip (metrics + live/interval status)."""
        parts: list[str] = []
        if self._last is not None:
            for spec in self.metrics:
                try:
                    parts.append(f"[bold]{spec.label}:[/bold] {spec.value(self._last)}")
                except Exception:
                    parts.append(f"[bold]{spec.label}:[/bold] —")
        for label, value in self._extra_metrics_cache:
            parts.append(f"[bold]{label}:[/bold] {value}")
        live = "[green]● live[/green]" if self._live else "[dim]○ paused[/dim]"
        status = f"{live} · every {self._interval}s · L pause · I interval"
        body = "   ".join(parts)
        self._set_metrics(f"{body}\n{status}" if body else status)

    def _render_metrics_message(self, markup: str) -> None:
        """Show a one-line message in the metrics strip."""
        self._set_metrics(markup)

    def _set_metrics(self, markup: str) -> None:
        try:
            self.query_one(f"#{self.id_prefix}-metrics", Static).update(markup)
        except Exception:
            pass


class OverviewView(MonitoringSubView):
    """Overview — the one-glance dashboard: QPS, connections, InnoDB rows."""

    id_prefix = "mon-overview"

    graphs = (
        _GraphSpec(
            "qps",
            "Queries/sec",
            lambda p, c: rate(p, c, "Queries"),
            color="cyan",
        ),
        _GraphSpec(
            "conns",
            "Threads connected",
            lambda p, c: c.gauge("Threads_connected"),
            unit="",
            color="green",
        ),
        _GraphSpec(
            "rows_read",
            "InnoDB rows read/sec",
            lambda p, c: rate(p, c, "Innodb_rows_read"),
            color="magenta",
        ),
        _GraphSpec(
            "rows_written",
            "InnoDB rows written/sec",
            lambda p, c: sum_rate(
                p, c, ("Innodb_rows_inserted", "Innodb_rows_updated", "Innodb_rows_deleted")
            ),
            color="yellow",
        ),
    )

    metrics = (
        _MetricSpec("Connections", lambda s: _fmt_conns(s)),
        _MetricSpec("Threads running", lambda s: str(int(s.gauge("Threads_running")))),
        _MetricSpec("Uptime", lambda s: _fmt_uptime(s.gauge("Uptime"))),
    )


def _buffer_pool_hit_rate(prev: Snapshot, cur: Snapshot) -> float:
    """InnoDB buffer pool hit rate (%) between two snapshots.

    hit% = 100 * (1 - disk_reads / logical_read_requests) over the interval.
    Returns 100.0 when there were no logical reads (nothing to miss).
    """
    requests = cur.gauge("Innodb_buffer_pool_read_requests") - prev.gauge(
        "Innodb_buffer_pool_read_requests"
    )
    disk = cur.gauge("Innodb_buffer_pool_reads") - prev.gauge("Innodb_buffer_pool_reads")
    if requests <= 0:
        return 100.0
    hit = 100.0 * (1.0 - (disk / requests))
    return max(0.0, min(100.0, hit))


def _pct_dirty(s: Snapshot) -> str:
    """Percentage of buffer pool pages that are dirty."""
    total = s.gauge("Innodb_buffer_pool_pages_total")
    dirty = s.gauge("Innodb_buffer_pool_pages_dirty")
    if total <= 0:
        return "—"
    return f"{100.0 * dirty / total:.1f}%"


def _history_list(s: Snapshot) -> str:
    """History list length (purge lag), or unknown when unavailable."""
    return str(s.history_list_length) if s.history_list_length >= 0 else "—"


class InnoDBView(MonitoringSubView):
    """InnoDB — buffer pool, flushing, row activity, and lock waits."""

    id_prefix = "mon-innodb"

    graphs = (
        _GraphSpec(
            "hit_rate",
            "Buffer pool hit rate",
            _buffer_pool_hit_rate,
            unit="%",
            color="green",
        ),
        _GraphSpec(
            "flushed",
            "Pages flushed/sec",
            lambda p, c: rate(p, c, "Innodb_buffer_pool_pages_flushed"),
            color="yellow",
        ),
        _GraphSpec(
            "rows_rw",
            "Rows read/sec",
            lambda p, c: rate(p, c, "Innodb_rows_read"),
            color="magenta",
        ),
        _GraphSpec(
            "row_lock_waits",
            "Row lock waits/sec",
            lambda p, c: rate(p, c, "Innodb_row_lock_waits"),
            color="red",
        ),
    )

    metrics = (
        _MetricSpec(
            "Buffer pool",
            lambda s: _fmt_bytes(s.var_float("innodb_buffer_pool_size")),
        ),
        _MetricSpec("Dirty pages", _pct_dirty),
        _MetricSpec("History list", _history_list),
        _MetricSpec("Log waits", lambda s: str(int(s.gauge("Innodb_log_waits")))),
    )


class LocksView(MonitoringSubView):
    """Locks & Contention — the live pulse of blocking on the server.

    Shows lock-wait rates and, as instant metrics, the current number of
    blocked sessions and the longest current wait (from sys.innodb_lock_waits,
    the same source as the Administration InnoDB Locks tab). This is the "is
    something blocked right now?" glance; go to Administration to see *who*.
    """

    id_prefix = "mon-locks"

    graphs = (
        _GraphSpec(
            "row_lock_waits",
            "Row lock waits/sec",
            lambda p, c: rate(p, c, "Innodb_row_lock_waits"),
            color="red",
        ),
        _GraphSpec(
            "row_lock_time_avg",
            "Avg row lock wait",
            lambda p, c: c.gauge("Innodb_row_lock_time_avg"),
            unit="ms",
            color="yellow",
        ),
        _GraphSpec(
            "table_locks_waited",
            "Table locks waited/sec",
            lambda p, c: rate(p, c, "Table_locks_waited"),
            color="magenta",
        ),
        _GraphSpec(
            "row_lock_current",
            "Row lock current waits",
            lambda p, c: c.gauge("Innodb_row_lock_current_waits"),
            unit="",
            color="cyan",
        ),
    )

    metrics = (
        _MetricSpec(
            "Current row-lock waits",
            lambda s: str(int(s.gauge("Innodb_row_lock_current_waits"))),
        ),
    )

    def _extra_metrics(self) -> list[tuple[str, str]]:
        """Blocked-session count and longest current wait from the sys schema."""
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.services.locks import fetch_lock_waits

        conn_result = getattr(self.app, "db_connection", None)
        if not isinstance(conn_result, ConnectionResult):
            return []
        try:
            waits = fetch_lock_waits(conn_result.connection)
        except Exception:
            return []
        if not waits:
            return [("Blocked sessions", "0")]
        longest = max(w.wait_age_secs for w in waits)
        return [
            ("Blocked sessions", str(len(waits))),
            ("Longest wait", f"{longest}s"),
        ]


def _connection_errors(s: Snapshot) -> str:
    """Sum of the Connection_errors_* counters (0 when none present)."""
    total = sum(v for k, v in s.status.items() if k.startswith("connection_errors_"))
    return str(int(total))


class ThroughputView(MonitoringSubView):
    """Throughput & Traffic — statement mix, network bytes, aborted connects."""

    id_prefix = "mon-throughput"

    graphs = (
        _GraphSpec(
            "selects",
            "SELECT/sec",
            lambda p, c: rate(p, c, "Com_select"),
            color="cyan",
        ),
        _GraphSpec(
            "writes",
            "Writes/sec (ins+upd+del)",
            lambda p, c: sum_rate(p, c, ("Com_insert", "Com_update", "Com_delete")),
            color="yellow",
        ),
        _GraphSpec(
            "net_in",
            "Bytes received/sec",
            lambda p, c: rate(p, c, "Bytes_received"),
            unit="B/s",
            color="green",
        ),
        _GraphSpec(
            "net_out",
            "Bytes sent/sec",
            lambda p, c: rate(p, c, "Bytes_sent"),
            unit="B/s",
            color="magenta",
        ),
    )

    metrics = (
        _MetricSpec("Received", lambda s: _fmt_bytes(s.gauge("Bytes_received"))),
        _MetricSpec("Sent", lambda s: _fmt_bytes(s.gauge("Bytes_sent"))),
        _MetricSpec("Slow queries", lambda s: str(int(s.gauge("Slow_queries")))),
        _MetricSpec("Aborted connects", lambda s: str(int(s.gauge("Aborted_connects")))),
        _MetricSpec("Conn errors", _connection_errors),
    )


class ReplicationMonView(MonitoringSubView):
    """Replication — a focused live replica-lag graph plus per-channel status.

    Unlike the counter-rate sub-tabs, this one samples replica lag from
    SHOW REPLICA STATUS (via the replication service) and reuses the same lag
    chart as the Administration Replication tab. On a non-replica it shows a
    short note rather than an empty graph.
    """

    id_prefix = "mon-repl"

    # No status-counter graphs; this view manages its own lag series + body.
    graphs = ()
    metrics = ()

    DEFAULT_CSS = """
    ReplicationMonView #mon-repl-lag {
        height: auto;
        padding: 1 2 0 2;
    }

    ReplicationMonView #mon-repl-body {
        height: 1fr;
        padding: 1 2;
    }
    """

    def __init__(self) -> None:
        """Initialize the replication view with its own lag series."""
        super().__init__()
        self._lag_series: list[int] = []

    def compose(self) -> ComposeResult:
        """Build the lag graph, the status body, and the metrics strip."""
        yield Static("", id="mon-repl-lag")
        yield Static("", id="mon-repl-body")
        yield Static("", classes="mon-metrics", id=f"{self.id_prefix}-metrics")

    def _sample(self) -> None:
        """Fetch replication state, append worst lag, and render."""
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.services.replication import fetch_replication

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self._render_metrics_message("[yellow]Not connected to a database.[/yellow]")
            return

        server_info = getattr(self.app, "server_info", None)
        try:
            info = fetch_replication(conn_result.connection, server_info)
        except Exception as e:
            self._render_metrics_message(f"[red]Error: {e}[/red]")
            return

        if not info.channels:
            self._set_body("[dim]This server is not a replica.[/dim]")
            self._render_lag([])
            self._extra_metrics_cache = []
            self._render_metrics()
            return

        lags = [c.seconds_behind for c in info.channels if c.seconds_behind is not None]
        if lags:
            self._lag_series.append(max(lags))
            if len(self._lag_series) > self._sample_cap:
                del self._lag_series[: len(self._lag_series) - self._sample_cap]

        self._render_lag(self._lag_series)
        self._set_body(self._build_body(info))
        self._extra_metrics_cache = []
        self._render_metrics()

    def _render_lag(self, series: list[int]) -> None:
        """Render the lag chart via the shared Administration renderer."""
        from mydba_tui.ui.screens.administration import _render_lag_chart

        lag = self.query_one("#mon-repl-lag", Static)
        if not series:
            lag.update("")
            return
        width = max(self.size.width - 4, 20)
        lag.update(_render_lag_chart(series, width, 6, self._interval))

    def _build_body(self, info: object) -> str:
        """Build a compact per-channel status body."""
        from mydba_tui.services.replication import ReplicationInfo, lag_trend

        assert isinstance(info, ReplicationInfo)
        lines: list[str] = []
        for ch in info.channels:
            name = f" (channel '{ch.channel}')" if ch.channel else ""
            io_c = "green" if ch.io_running.lower() == "yes" else "red"
            sql_c = "green" if ch.sql_running.lower() == "yes" else "red"
            if ch.seconds_behind is None:
                lag = "[red]NULL (not replicating)[/red]"
            else:
                lag = f"{ch.seconds_behind}s {lag_trend(self._lag_series)}"
            lines.append(f"[bold cyan]Replica{name}[/bold cyan]")
            lines.append(
                f"  IO [{io_c}]{ch.io_running or '—'}[/{io_c}]  ·  "
                f"SQL [{sql_c}]{ch.sql_running or '—'}[/{sql_c}]  ·  Lag {lag}"
            )
            lines.append(f"  Source: {ch.source_host or '—'}:{ch.source_port or '—'}")
            lines.append("")
        return "\n".join(lines)

    def _set_body(self, markup: str) -> None:
        try:
            self.query_one("#mon-repl-body", Static).update(markup)
        except Exception:
            pass


class MonitoringScreen(Screen[None]):
    """Monitoring — a lightweight live dashboard, organized into sub-tabs."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh", key_display="R", priority=True),
        Binding("l", "toggle_live", "Live On/Off", key_display="L"),
        Binding("i", "cycle_interval", "Interval", key_display="I"),
        Binding("escape", "go_back", "Back", key_display="Esc"),
        Binding("f10", "quit", "Exit", key_display="F10"),
    ]

    CSS = """
    MonitoringScreen {
        overflow: hidden;
    }

    MonitoringScreen #monitoring-tabs {
        height: 1fr;
    }

    MonitoringScreen Footer {
        dock: bottom;
    }

    MonitoringScreen TabPane {
        padding: 0;
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        """Build the tabbed monitoring layout."""
        yield Header()
        yield StatusBar(id="status-bar")
        with TabbedContent(id="monitoring-tabs"):
            with TabPane("Overview", id="mon-tab-overview"):
                yield OverviewView()
            with TabPane("InnoDB", id="mon-tab-innodb"):
                yield InnoDBView()
            with TabPane("Throughput", id="mon-tab-throughput"):
                yield ThroughputView()
            with TabPane("Locks", id="mon-tab-locks"):
                yield LocksView()
            with TabPane("Replication", id="mon-tab-replication"):
                yield ReplicationMonView()
        yield Footer()

    def __init__(self) -> None:
        """Initialize screen-level live/interval/timer state."""
        super().__init__()
        # The screen owns the single sampling timer + live/interval state so
        # every sub-view collects continuously (no gaps when switching tabs).
        self._live: bool = True
        self._interval: int = 5
        self._timer: Timer | None = None

    def on_mount(self) -> None:
        """Sync the status bar and start the single, screen-wide sampling timer."""
        self._sync_status_bar()
        self._interval = _current_interval(self.app)
        self._push_context()
        self._sample_all()
        self._timer = self.set_interval(self._interval, self._on_tick)

    def on_screen_resume(self) -> None:
        """Sync status and sample immediately when returning to the screen."""
        self._sync_status_bar()
        self._sample_all()

    def _views(self) -> list[MonitoringSubView]:
        """All monitoring sub-views, regardless of which tab is visible."""
        return list(self.query(MonitoringSubView))

    def _push_context(self) -> None:
        """Share the current interval/live state with every sub-view."""
        for view in self._views():
            view.set_context(self._interval, self._live)

    def _on_tick(self) -> None:
        """Timer callback — sample every sub-view while live (even if hidden)."""
        if not self._live:
            return
        self._sample_all()

    def _sample_all(self) -> None:
        """Drive one sample on every sub-view so all histories stay continuous."""
        for view in self._views():
            try:
                view.sample()
            except Exception:
                pass

    def action_refresh(self) -> None:
        """Sample all sub-views once now."""
        self._sample_all()

    def action_toggle_live(self) -> None:
        """Turn live sampling on or off for the whole dashboard."""
        self._live = not self._live
        self._push_context()
        self.notify("Live updates on." if self._live else "Live updates paused.")
        # Re-render the status lines to reflect the change immediately.
        for view in self._views():
            view._render_metrics()

    def action_cycle_interval(self) -> None:
        """Cycle the shared refresh interval and restart the single timer."""
        self._interval = _cycle_interval(self.app)
        self._push_context()
        if self._timer is not None:
            self._timer.stop()
        self._timer = self.set_interval(self._interval, self._on_tick)
        for view in self._views():
            view._render_metrics()
        self.notify(f"Interval: {self._interval}s.")

    def _sync_status_bar(self) -> None:
        """Sync the status bar with the current connection state."""
        status = getattr(self.app, "connection_status", "")
        if status:
            try:
                self.query_one("#status-bar", StatusBar).status_text = status
            except Exception:
                pass

    def action_go_back(self) -> None:
        """Return to the previous screen."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()
