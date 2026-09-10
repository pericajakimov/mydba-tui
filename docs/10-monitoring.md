# Monitoring

## Purpose

The Monitoring module provides a lightweight, real-time overview of the operational state of the connected MySQL server.

Its purpose is **situational awareness**, not deep performance analysis.

`mydba` is not intended to replace monitoring systems such as PMM, Grafana, CloudWatch, or similar tools. Instead, it should allow a DBA connected over SSH to quickly answer the question:

> "Is this server currently under load, and what is happening right now?"

---

# Design Goals

The Monitoring module should:

- Load quickly.
- Consume minimal server resources.
- Require no additional configuration.
- Present only the most useful operational metrics.
- Be readable in a terminal.
- Avoid overwhelming the user.

---

# Philosophy

Monitoring is intentionally kept simple.

When detailed performance analysis is required, dedicated monitoring platforms should be used.

The Monitoring page exists to provide a quick operational snapshot while working interactively on the server.

---

# Refresh Model

Monitoring updates automatically (live) at a configurable refresh interval.
Because it is a dashboard, live updates are ON by default when the screen is
opened (unlike the Administration tabs, which load once and are opt-in live).

The interval is the shared `refresh_interval` setting, cycled in-app through the
fixed choices 5, 10, 30, and 60 seconds with the `I` key (the same setting and
choices used by the Administration live tabs). The default is 5 seconds. Live
updates can be paused/resumed with `L`, and a manual sample is available with
`R`.

Every tick executes a single lightweight `SHOW GLOBAL STATUS` (plus a couple of
small variable/metrics reads). Per-second rates (queries/sec, bytes/sec, ...)
are computed as the delta of a counter between two consecutive snapshots divided
by the elapsed time; a counter going backwards (a server restart) is treated as
zero rather than a spike.

While the Monitoring screen is open, **all** sub-tabs sample on the single
screen-level timer — not just the visible one — so every graph's history stays
continuous and switching sub-tabs never leaves a stale gap. Collected history
is session-local and rolling; nothing is persisted.

> Future enhancement: collect metrics in the background even while the user is
> working elsewhere in the app (SQL Workspace, Object Browser), so returning to
> Monitoring shows already-populated graphs. This would most likely run on a
> dedicated sampling connection separate from the interactive connection, so
> background sampling never competes with interactive queries (the current
> single shared connection is used single-threaded, so it cannot sample in the
> background without blocking interactive work).

---

# Screen Layout

The Monitoring screen is reached from the Object Browser with the `M` key. It is
organized into sub-tabs (like the Administration Performance tab), each a
compact 2×2 grid of live graphs plus an instant-metrics strip.

## Graph boxes and the time axis

Each graph sits in its own bordered box titled with the metric name, and shows
a current/peak readout, a y-axis (max at top, 0 at bottom, with units), and a
fixed-window x-axis. The x-axis always spans a fixed window (30 minutes): the
newest sample sits at the right edge ("now") and the line fills from the right
toward the left as history accumulates — the window does not grow. The same
fixed-window braille chart renderer is shared with the Replication tab's
replica-lag graph so they look and behave identically.

## Sub-tabs

- **Overview** — the one-glance dashboard: queries/sec, threads connected,
  InnoDB rows read/sec, InnoDB rows written/sec; instant metrics for connections
  used/max, threads running, and uptime.
- **InnoDB** — buffer pool hit rate (%), pages flushed/sec, rows read/sec, row
  lock waits/sec; instant metrics for buffer pool size, dirty-page percentage,
  history list length (purge lag), and log waits.
- **Throughput** — statement mix (SELECT/sec vs writes/sec = insert+update+
  delete, both from the global `Com_*` command counters — i.e. statements
  issued, not rows or engine operations), network bytes received/sec and
  sent/sec; instant metrics for total bytes in/out, slow queries, aborted
  connects, and connection errors.
- **Locks** — the live pulse of contention: row lock waits/sec, average row lock
  wait time, table locks waited/sec, current row-lock waits; instant metrics for
  the current blocked-session count and longest current wait (from the same sys
  source as the Administration InnoDB Locks tab). Go to Administration to see
  *who* is blocked.
- **Replication** — a focused live replica-lag graph plus per-channel IO/SQL
  thread state and seconds behind, reusing the Administration replication
  service and lag chart. On a non-replica it shows a short note instead of a
  graph.

## Instant metrics

Each sub-tab has a metrics strip below its graphs for values better shown as
numbers than as graphs (see the per-sub-tab lists above), followed by a status
line showing whether live updates are on and the current interval.

---

# Server Awareness

The Monitoring module adapts to the connected server.

Examples include:

- Oracle MySQL
- AWS Aurora
- Percona Server
- Percona XtraDB Cluster

Only metrics that can be reliably collected on the detected platform should be displayed.

---

# Performance Impact

Monitoring queries must be lightweight.

The module should avoid:

- Expensive table scans
- Large metadata queries
- Frequent complex joins

The Monitoring page must never become a noticeable source of database load.

All metrics are best-effort: the Locks sub-tab's blocked-session count needs the
sys schema (absent on MariaDB), the InnoDB history list length needs the
`trx_rseg_history_len` metric enabled, and some counters depend on
performance_schema instruments. Where a value can't be read it degrades to a
dash or an empty graph rather than an error.

---

# Pause and Resume

Live sampling can be paused and resumed at any time with the `L` key, and a
manual sample is available with `R`. Sampling runs only while the Monitoring
screen is open; leaving it (or losing the connection) stops sampling, and it
resumes when the screen is shown again.

---

# Historical Data

The Monitoring module displays only data collected during the current application session.

It is **not** a historical monitoring system.

Long-term metrics remain the responsibility of dedicated monitoring platforms.

---

# SQL Transparency

All SQL executed by the Monitoring module is written to the SQL log.

This allows DBAs to understand exactly how each metric is calculated and optimize or replace queries in future versions if needed.

---

# Future Enhancements

Possible future additions include:

- Buffer Pool activity
- Redo log throughput
- Temporary table creation rate
- Network traffic
- Replica topology overview
- Group Replication status
- Galera / PXC cluster status
- Aurora-specific replica information
- Custom user-defined monitoring widgets

These features are intentionally deferred to keep the initial implementation focused and lightweight.

---

# Design Principles

The Monitoring module follows these principles:

- Lightweight by default.
- Operational awareness over deep analytics.
- Minimal impact on the database.
- Automatic refresh only while active.
- Clear visual presentation.
- SQL transparency.
- Extensible architecture.
