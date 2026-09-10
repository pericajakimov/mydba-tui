# Administration

## Purpose

The Administration module provides quick access to operational information required for day-to-day database administration.

Its objective is to replace the repetitive execution of common administrative SQL statements with a structured, keyboard-driven interface while remaining completely transparent about the SQL executed.

The Administration module focuses on operational visibility rather than configuration management.

---

# Design Goals

The Administration module should:

- Provide immediate access to operational information.
- Eliminate repetitive administrative queries.
- Present information in a consistent format.
- Support fast filtering.
- Avoid unnecessary complexity.
- Remain responsive on busy production systems.

---

# Available Sections

The Administration module contains the following sections:

- Process List
- Users
- Replication
- Performance
- Variables
- Status
- Locks
- Transactions
- Connections
- Metadata Locks
- InnoDB Status

Additional sections may be introduced in future versions.

---

# Process List

The Process List provides a live view of active MySQL sessions. It is the first
Administration section and is reached from the Object Browser with the `A` key.

## Query source

The query is chosen based on the detected server so the columns are consistent
across backends:

- MySQL family (Oracle MySQL, Percona, PXC, Aurora) 8.0+ → `performance_schema.processlist`
- MariaDB → `information_schema.PROCESSLIST`
- Anything else → `SHOW FULL PROCESSLIST`

On the `performance_schema` path the client program name is sourced from
`performance_schema.session_connect_attrs` (`program_name`), the same way MySQL
Workbench does it. On the other paths the Program column is empty. mydba's own
connections report `program_name = mydba`, so the tool identifies itself here.

All statements mydba runs internally are tagged with a `/* mydba */` marker in
their text, making them easy to spot in the Info column; queries you run from
the SQL Workspace are sent exactly as written, without any tag.

## Columns

Id, User, Host, db, Command, Time, State, Program, Info.

- Host is shown as the IP/hostname only; the client source port is stripped.
- Time is shown as raw seconds in the table (compact and sortable).
- State and Info are truncated in the table; the full values appear in the
  detail view and when opened in the SQL Workspace.

## Live view and refresh

The Process List loads its data once when the tab is opened and then stays
still — it does not poll the server on its own. Live updates are opt-in: press
`L` to start refreshing on an interval and `L` again to stop. `R` refreshes
once at any time, and `I` cycles the refresh interval through a fixed set of
choices (5, 10, 30, 60 seconds; the choice is shared by every live tab and
persisted to `refresh_interval`). While live, the cursor position is preserved
across refreshes by session id, and the info line shows the live state and
interval. Only the visible tab queries the server.

## Filtering

Filtering is immediate and operates on the currently displayed data (no query
is rerun). The filter matches across User, Host, db, Command, State, Program,
and Info. A separate toggle hides sleeping (`Command = Sleep`) connections.

## Session detail

Activating a session (`Enter`) opens a detail view showing every field in full
(including the complete, untruncated State) plus the syntax-highlighted query
when the session has one.

## Terminating sessions

A selected session's running query can be terminated with `KILL QUERY`, or the
whole session with `KILL`. Both require confirmation, and the tool refuses to
kill the application's own session.

## Open in SQL Workspace

A selected session's query can be sent to the SQL Workspace (`W`) for
examination and EXPLAIN. The query is prefixed with a comment block describing
the session (connection id, user, host, db, command, time — with a
human-readable duration — state, and program). If the editor already has
content the query is appended; otherwise it replaces the empty editor.

## Keybindings

| Key | Action |
|-----|--------|
| R | Refresh now |
| L | Start / stop live updates |
| I | Cycle the refresh interval |
| S | Toggle hiding sleeping connections |
| / | Filter (Enter keeps, Esc clears) |
| Enter | Session detail |
| K | Kill query |
| Shift+K | Kill connection |
| W | Open query in SQL Workspace |
| Esc | Back to Object Browser |

The goal is to quickly identify problematic sessions without writing custom queries.

---

# Users

The Users section lists MySQL accounts, each assigned to a logical group, with
detailed grants shown on demand. It is a manual-refresh Administration tab
(placed after Metadata Locks); accounts change rarely, so there is no
auto-refresh.

## SQL-driven grouping

The grouping is defined entirely in `sql/admin/users.sql`, not in application
code. A CASE expression over `mysql.user` (and correlated subqueries against
`mysql.db` for schema-level privileges) assigns each account a group, and an
outer query maps each group name to a colour. Anyone can edit this file to
change the rules, add groups, or recolour them — the application only renders
the result.

The default rules classify accounts into (first match wins):

- **System Users** — reserved server accounts (`root`, `mysql.sys`, etc.)
- **Admin Users** — global SUPER, or global CREATE + ALTER + DROP
- **Personal Users** — the username contains a dot (e.g. `name.surname`)
- **Application Users** — CREATE + ALTER + DROP on at least one schema (checked
  before read-only so an app account with extra SELECT grants stays here)
- **Monitoring Users** — global PROCESS (checked before Replication, since a
  monitoring account often also holds replication privileges)
- **Replication Users** — global REPLICATION SLAVE or REPLICATION CLIENT
- **Read-Only Users** — global SELECT, or schema-level SELECT with no writes
- **Special Purpose Users** — anything else

## Presentation

Columns: Group, User, Host, Locked, Password Expired, Password Changed, Auth
Plugin. Rows are ordered by group, then user, then host, and the group name is
colour-coded (colours come from the SQL, with an automatic palette fallback).

- Filtering (`/`) matches across group, user, host, and auth plugin; `Esc`
  clears. Refresh (`r`) reloads on demand.
- `Enter` opens a detail view with the account summary and its grants, fetched
  on demand with `SHOW GRANTS` (the one place per-account grant detail is run).

---

# Replication

The Replication section is a read-only, role- and vendor-aware cockpit for
everything about replication on the connected server: a health verdict, a live
replica-lag graph, per-channel replica status, the local binary logs, GTID
state, and Galera/PXC cluster state. It is the last Administration tab.

A server can play several roles at once (a PXC node that is also an async
replica, or a mid-chain host that is both a replica and a primary), so each
section is shown only when it applies. A plain standalone server shows a simple
"standalone" verdict.

## Health verdict

A colored banner summarises the overall state, computed in Python from the
gathered fields (worst state wins): BROKEN (a stopped/errored thread) →
LAGGING (a running replica at or over the lag threshold) → HEALTHY → GALERA
(synced cluster) → PRIMARY (has connected replicas) → STANDALONE.

## Replica lag graph

When the host is a replica, a braille line-chart (drawn without any external
charting dependency) shows recent replica lag with a y-axis (peak and 0) and a
relative time x-axis. A healthy replica reads as a flat line pinned at 0 rather
than an empty panel. The rolling window holds up to 30 minutes of history; the
sample cadence follows the refresh interval, and the x-axis label reflects the
actual span.

## Replica section (per channel)

For each replication channel: IO and SQL thread state (colored), lag with a
trend arrow, source host/port, the source-log read and applied positions,
retrieved-but-not-yet-applied bytes ("Unapplied", when both positions are on
the same source file), relay-log file/position, total relay-log disk usage
(the sum of all relay logs on disk, matching PMM's relay-log metric), applier
threads (parallel worker count/type and busy workers, or single-threaded),
auto-position, and any IO/SQL thread errors. Sections are laid out as an
aligned label/value block (like `\G` vertical output).

## Binary Logs

The local host's binary logs (a replica may write its own binlogs for chained
replication, so this is deliberately not called "primary"): current binlog file
and position, format, row image, row metadata, and the binary-log count with
total size.

## Connected Replicas

Replicas connected to this host (from `SHOW REPLICAS`) with server id, host,
and port — shown on a primary or on a mid-chain replica, so chained replication
is visible.

## GTID

GTID mode with the Retrieved, Executed, and Purged sets, each rendered on its
own lines below its label (the sets can be long and contain newlines).

## Cluster (Galera / PXC)

For a wsrep node: cluster name, status, local state (colored by synced), node
count, and flow-control pause fraction. The wsrep status counters are queried
only when the server is actually a cluster node.

## Efficient data collection

The full picture is gathered with a handful of queries. All the scalar global
variables it needs are read in a single batched `SHOW GLOBAL VARIABLES WHERE
Variable_name IN (...)` rather than one query per variable; the wsrep status
counters are read in one batched query and only on a cluster node. Every query
is best-effort, tagged, and written to the SQL log; a missing privilege or
unsupported feature yields empty data rather than an error.

## Live updates

Like the other operational tabs, Replication loads once when opened and does
not poll on its own. Press `L` to start live updates (the graph then samples on
the refresh interval), `L` again to stop, `R` to refresh once, and `I` to cycle
the refresh interval. A status line under the banner shows whether live updates
are on and at what interval.

## Keybindings

| Key | Action |
|-----|--------|
| R | Refresh now |
| L | Start / stop live updates |
| I | Cycle the refresh interval |
| Esc | Back to Object Browser |

This section is read-only. Actions that change replication (start/stop, reset,
skip) are intentionally left to the SQL Workspace.

---

# Performance

The Performance section is a read-only cockpit over the MySQL `sys` schema — the
set of diagnostic views that package raw performance_schema data into the
questions a DBA actually asks during an incident ("what's slow, who's driving
load, where's the I/O, which indexes are wasted"). It is a parent tab that hosts
a family of sub-tabs, each a summary grid whose rows drill down into related
breakdown views.

## Summary grid and drill-down

Every sub-tab shows a `sys` summary view as a sortable, filterable grid (the
same live machinery as the other tabs: loads once, opt-in live updates with
`L`, interval with `I`, manual refresh with `R`, filter with `/`). Pressing
`Enter` on a row opens a drill-down detail keyed to that row — the sys schema's
"summary + `_by_*` breakdowns" design surfaced directly. Each breakdown is shown
as a sub-tab inside the detail modal.

## Sub-tabs

- **Top Queries** — `sys.statement_analysis`: normalized statement digests by
  total latency (executions, avg/max latency, rows examined, tmp tables, full
  scans). `Enter` shows the full normalized statement and a captured sample;
  `W` sends it to the SQL Workspace to EXPLAIN.
- **Users** — `sys.user_summary`: per-user activity. `Enter` drills into
  statement latency, statement types, stages, and file I/O (by total and by
  type) for that user.
- **Hosts** — `sys.host_summary`: the same breakdowns grouped by client host.
- **Waits** — `sys.waits_global_by_latency`: global wait events by latency.
  `Enter` breaks a wait event down by user and by host.
- **I/O** — `sys.io_global_by_file_by_bytes`: file I/O hotspots. `Enter` shows
  the server-global I/O by wait type and by thread as context.
- **Tables** — `sys.schema_table_statistics`: per-table access statistics.
  `Enter` shows that table's index statistics and its InnoDB buffer-pool
  footprint.
- **Indexes** — `sys.schema_unused_indexes`: indexes with no recorded use
  (removal candidates). `Enter` lists redundant indexes, each with a
  ready-to-run `DROP INDEX` statement.
- **Full Scans** — `sys.statements_with_full_table_scans`: statements that
  scanned without an index. Same digest drill-down and `W` as Top Queries.
- **Memory** — `sys.memory_global_by_current_bytes`: current memory by
  allocation type. `Enter` shows current memory by user and by thread.

## Availability

The Performance tab depends on the `sys` schema and performance_schema. Both are
present and enabled by default on MySQL 5.7+/8.0+, Percona, and Aurora. On
MariaDB (which has no `sys` schema) or when a required performance_schema
consumer/instrument is disabled, the affected grid shows an explanatory
"unavailable" note instead of data — nothing errors.

## Read-only

Like the rest of Administration, this section only reads. Actionable follow-ups
— running `EXPLAIN`, dropping a redundant index — are done by sending the
statement to the SQL Workspace (`W` on the digest tabs) rather than executing
anything here.

## Keybindings

| Key | Action |
|-----|--------|
| R | Refresh now |
| L | Start / stop live updates |
| I | Cycle the refresh interval |
| / | Filter (Enter keeps, Esc clears) |
| Enter | Row drill-down detail |
| W | Open statement in SQL Workspace (Top Queries, Full Scans) |
| Esc | Back to Object Browser |

---

# Variables

The Variables section provides access to MySQL global variables. It is a tab in
the Administration screen, reached from the Object Browser with `A`.

It lists all global variables (from `SHOW GLOBAL VARIABLES`) as a Variable/Value
table, sorted by name.

- Filtering (`/`) is immediate and matches across both the variable name and
  its value. `Esc` clears the filter.
- Refresh (`r`) reloads on demand; variables rarely change, so there is no
  auto-refresh.
- Long values are truncated in the table; `Enter` opens the full value.

> A "non-default only" view (showing just variables that differ from server
> defaults) was considered but deferred: MySQL exposes no reliable catalog of
> per-version, per-vendor defaults, so such a view cannot be computed
> accurately. Strong filtering covers the common need to locate a variable.

---

# Status

The Status section provides access to global status counters. It is a tab in
the Administration screen and shares the same key/value presentation as the
Variables tab.

It lists all global status counters (from `SHOW GLOBAL STATUS`) as a
Name/Value table, sorted by name.

- Filtering (`/`) is immediate and matches across both the counter name and its
  value. `Esc` clears the filter.
- Refresh (`r`) reloads on demand. Unlike Variables, Status also reloads each
  time the tab is shown, since counters change over time.
- `Enter` opens the full value of the selected counter.

This section belongs to operational information rather than configuration.

---

# InnoDB Locks

The InnoDB Locks section surfaces InnoDB row-lock contention — which session is
blocked and which session is blocking it — sourced from the sys schema
(`sys.innodb_lock_waits`), enriched with user/host from the process list. It is
a live Administration tab, placed after Transactions.

Columns: Wait Age, Locked Table, Waiting PID, Waiting User, Waiting Mode,
Waiting Query, Blocking PID, Blocking User, Blocking Mode, Blocking Query. Rows
are sorted with the longest-waiting first. The lock mode is shown as InnoDB's
short code in the table (e.g. `X`, `X,GAP`).

Like the other live views, it loads once and supports opt-in live updates
(`L` starts/stops, `I` cycles the interval, `R` refreshes now) and filtering
(`/`, matching users, table, lock modes, and queries).

Actions:

- `Enter` opens a detail view showing the waiting and blocking sessions in
  full, with their queries highlighted and their lock modes explained (e.g.
  `X,REC_NOT_GAP (Exclusive, record only (no gap))`). A blocking session that
  has gone idle reports no current query (a known InnoDB limitation), so the
  detail view also shows the blocking session's recent statement history from
  performance_schema — revealing what it ran to acquire the lock.
- `k` kills the blocking connection to release the wait (with confirmation and
  a guard against killing the tool's own session).

The healthy default is an empty list (nothing blocked). The section relies on
the sys schema; where it is unavailable (e.g. MariaDB or an uninstalled sys
schema) the list is empty.

The objective is to quickly identify blocking situations without reading raw
metadata tables.

---

# Transactions

The Transactions section provides visibility into active InnoDB transactions.
It is a live Administration tab (after Connections), sourced from
`information_schema.innodb_trx` joined to the process list for each
transaction's user, host, and database.

Columns: Trx ID, Conn ID, User, Host (IP), DB, State, Age (human-readable),
Rows Locked, and Query. Rows are sorted with the longest-running transactions
first, so stuck or slow transactions surface at the top.

Like the other live views, it loads once and supports opt-in live updates
(`L` starts/stops, `I` cycles the interval, `R` refreshes now) and filtering
(`/`, matching user, host, db, state, and query).

Actions:

- `Enter` opens a detail view with every field in full plus the transaction's
  statement history (see below).
- `w` opens the transaction's query in the SQL Workspace with a metadata header.
- `k` kills the connection holding the transaction (with confirmation and a
  guard against killing the tool's own session).

## Current statement, statement history, and rows locked

`innodb_trx.trx_query` only reflects the statement a transaction is *currently*
executing. A transaction that has run some statements and is now waiting for
COMMIT (idle in transaction) reports no current query. To make such
transactions understandable, the detail view also shows the connection's recent
**statement history** from `performance_schema.events_statements_history`
(most recent first, with timings). This is best-effort: if performance_schema
statement history is unavailable or disabled, the detail view says so.

`Rows Locked` is InnoDB's approximate count (`trx_rows_locked`) and includes
index and gap locks, so it can exceed the number of rows in the table; it is
labeled as an estimate.

The purpose is to help identify long-running or problematic transactions.

---

# Connections

The Connections section presents connection statistics grouped by User and
Client Host. It is the second Administration tab, right after the Process List,
and is derived from the same live session data (the process list is aggregated
in memory by `(user, host)`).

The client host is displayed as the IP address without the client port, so all
connections from the same source collapse into one group regardless of client
port. For each group the number of active connections is shown, sorted with the
heaviest sources first.

Like the Process List, it is a live-capable view:

- Loads once; opt-in live updates with `L` (start/stop), `I` cycles the
  interval, and `R` refreshes now.
- Filtering (`/`) matches across User and Host; `Esc` clears.

Only the visible tab queries the server; background tabs do not refresh.

The purpose is to quickly understand connection distribution across
applications and users.

---

# Metadata Locks

The Metadata Locks section surfaces table metadata-lock (MDL) contention — the
classic "Waiting for table metadata lock" case, e.g. an `ALTER TABLE` blocked
by an open transaction that still holds a shared lock on the table. It is
sourced from the sys schema (`sys.schema_table_lock_waits`) and placed after the
InnoDB Locks tab.

Columns: Wait Age, Object, Waiting PID, Waiting Account, Waiting Lock, Waiting
Query, Blocking PID, Blocking Account, Blocking Lock. Rows are sorted
longest-waiting first.

Like the other live views it loads once and supports opt-in live updates
(`L` starts/stops, `I` cycles the interval, `R` refreshes now) and filtering
(`/`, matching accounts, object, lock types, and queries).

Actions:

- `Enter` opens a detail view with the waiting and blocking sessions, the lock
  types explained in full (e.g. `EXCLUSIVE (Exclusive)`), and — because the MDL
  view carries no blocking query — the blocking session's recent statement
  history from performance_schema (which reveals what it ran to hold the lock).
- `k` kills the blocking connection to release the wait (with confirmation and
  a guard against killing the tool's own session).

The section relies on the sys schema; where it is unavailable (e.g. MariaDB or
an uninstalled sys schema) the list is empty. The healthy default is empty
(nothing blocked).

---

# InnoDB Status

The InnoDB Status section provides a concise operational summary rather than the complete `SHOW ENGINE INNODB STATUS` output.

Typical information includes:

- History List Length
- Active Transactions
- Latest Deadlock Information

The goal is to expose the information most frequently required during operational troubleshooting.

---

# Filtering

Where applicable, lists should support dynamic filtering.

Filtering should be immediate and operate on the currently displayed data.

The user should not need to rerun queries simply to narrow the visible results.

---

# Refresh

Every Administration tab loads its data once when opened and does not poll the
server on its own. Refreshing is always available on demand with `R`.

The live-capable tabs (Process List, Connections, Transactions, InnoDB Locks,
Metadata Locks, and Replication) additionally offer opt-in **live updates**:

- `L` starts and stops live updates. Live updates are always off until turned
  on — nothing auto-starts.
- `I` cycles the refresh interval through a fixed set of choices — 5, 10, 30,
  and 60 seconds. The choice is shared by all live tabs and persisted to the
  `refresh_interval` setting.
- Only the visible tab queries the server; a background tab never refreshes.

Manual-only tabs (Users, Variables, Status) load once and refresh with `R`;
they have no live-update option. Status additionally reloads each time its tab
is shown, since counters change over time.

---

# SQL Transparency

All SQL executed by the Administration module is recorded in the SQL log.

The application should never hide which statements are executed to retrieve administrative information.

---

# Design Principles

The Administration module follows these principles:

- Operational information before configuration.
- Fast access to commonly used administrative data.
- Dynamic filtering where appropriate.
- Concise presentation.
- SQL transparency.
- Familiar MySQL terminology.
- Consistent user interface.
```