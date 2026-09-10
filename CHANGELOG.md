# Changelog

All notable changes to **mydba** will be documented in this file.

The project follows the principles of **Keep a Changelog** and **Semantic Versioning**.

---

## [Unreleased]

### Added

#### Administration

- Tabbed Administration screen (reached from the Object Browser with `A`),
  navigated like the Object Browser tabs.
- Performance tab (last): a read-only cockpit over the MySQL `sys` schema with
  nine diagnostic sub-tabs — Top Queries (statement_analysis), Users
  (user_summary), Hosts (host_summary), Waits (waits_global_by_latency), I/O
  (io_global_by_file_by_bytes), Tables (schema_table_statistics), Indexes
  (schema_unused_indexes), Full Scans (statements_with_full_table_scans), and
  Memory (memory_global_by_current_bytes). Each sub-tab is a filterable summary
  grid with opt-in live updates; pressing Enter drills a row down into its
  related `_by_*` breakdown views (shown as sub-tabs in a detail modal), keyed
  to the selected user/host/wait/table. The statement tabs open the full
  normalized statement and a captured sample, sendable to the SQL Workspace
  (`W`) to EXPLAIN; the Indexes drill-down lists redundant indexes with
  ready-to-run DROP statements. All queries are best-effort and tagged: the tab
  degrades gracefully where the sys schema/performance_schema are unavailable
  (e.g. MariaDB). Read-only.
- Replication tab (last): a read-only, role- and vendor-aware cockpit with a
  colored health verdict (HEALTHY/LAGGING/BROKEN/PRIMARY/GALERA/STANDALONE), a
  live replica-lag graph (a dependency-free braille line-chart with a relative
  time axis and up to 30 minutes of history), per-channel replica status
  (threads, lag with trend, source and applied positions, unapplied bytes,
  relay-log file/position and total relay-log disk usage, applier worker
  info), the local Binary Logs (file/position, format, row image, row
  metadata, count and total size), connected replicas (for chained
  replication), GTID state (Retrieved/Executed/Purged), and Galera/PXC cluster
  state. Scalar variables are read in one batched query; the wsrep status
  counters only on a cluster node.
- Live-updates model across the live-capable tabs (Process List, Connections,
  Transactions, InnoDB Locks, Metadata Locks, Replication): each tab loads its
  data once and no longer auto-refreshes on open. Live updates are opt-in and
  off by default — `L` starts/stops them, `R` refreshes on demand, and `I`
  cycles the refresh interval through fixed choices (5, 10, 30, 60 seconds),
  shared across tabs and persisted. Replaces the previous pause/resume model.
- Variables tab: all global variables as a sorted Variable/Value table with
  immediate name+value filtering, manual refresh, and a full-value view on
  Enter.
- Status tab: all global status counters in the same key/value presentation;
  reloads on each visit since counters change over time.
- Connections tab (second, after Process List): live connection counts grouped
  by User and Host (IP), sorted by count, with opt-in live updates and filter.
- Transactions tab (after Connections): active InnoDB transactions, longest
  running first, with opt-in live updates, filter, kill-connection, open-query-
  in-workspace, and a detail view including the connection's statement history
  from performance_schema.
- InnoDB Locks tab (after Transactions): InnoDB row-lock waits from the sys
  schema showing blocked and blocking sessions with lock modes, opt-in live
  updates, filter, and kill-blocking-connection. The detail view shows both
  queries, explains the lock modes, and includes the blocking session's recent
  statement history (useful when the blocker is idle).
- Metadata Locks tab (after InnoDB Locks): table metadata-lock waits from the
  sys schema (the "Waiting for table metadata lock" case) with the locked
  object, waiting/blocking accounts and lock types, filter, kill-blocker, and a
  detail view including the blocking session's statement history.
- Session statement history is presented as a compact table (index, duration,
  statement) in the Transactions, InnoDB Locks, and Metadata Locks detail views.
- Users tab (after Metadata Locks): MySQL accounts with a logical group derived
  entirely in SQL (System/Admin/Personal/Application/Monitoring/Replication/
  Read-Only/Special Purpose), colour-coded group names, filtering, and grants
  shown on demand via a detail view. Manual refresh (no auto-refresh).
- Shared LiveTableView base underlying the Process List, Connections,
  Transactions, InnoDB Locks, and Metadata Locks views (load-once, opt-in live
  updates, interval cycling, filter, cursor preservation). A `supports_live`
  flag lets manual-only views (Users) reuse the table/filter/detail machinery
  without any live-update controls.
- Administration tabs only query the server while visible; background tabs
  never refresh the shared connection.
- Process List: a live view of active MySQL sessions, now the first
  Administration tab. The query source is chosen per server
  (`performance_schema.processlist` for MySQL 8.0+, `information_schema` for
  MariaDB, `SHOW FULL PROCESSLIST` otherwise).
- Columns: Id, User, Host (IP only), db, Command, Time, State, Program, Info.
  The Program name is sourced from `session_connect_attrs` on the
  performance_schema path.
- Loads once, with opt-in live updates (`L`), manual refresh (`R`), and cursor
  position preserved across refreshes.
- Immediate client-side filtering across fields and a hide-sleeping toggle.
- Session detail view (`Enter`) showing all fields in full plus the
  syntax-highlighted query.
- Terminate a session's query (`KILL QUERY`) or the whole session (`KILL`),
  with confirmation and a guard against killing the tool's own session.
- Open a session's query in the SQL Workspace (`W`) with a metadata comment
  header (including a human-readable duration) for examination and EXPLAIN.

#### Monitoring

- Monitoring screen (reached from the Object Browser with `M`): a lightweight
  live dashboard for quick situational awareness, organized into sub-tabs —
  Overview (queries/sec, connections, InnoDB rows read/written), InnoDB (buffer
  pool hit rate, pages flushed, row activity, lock waits, plus buffer pool /
  dirty pages / history list / log waits), Throughput (SELECT vs write statement
  rates from the Com_* counters, network bytes in/out, slow queries, aborted
  connects, connection errors), Locks (lock-wait rates and the live blocked-
  session count), and Replication (a replica-lag graph reusing the
  Administration replication service).
- Each sub-tab is a 2×2 grid of bordered braille graphs plus an instant-metrics
  strip. Metrics are computed from one cheap `SHOW GLOBAL STATUS` snapshot per
  tick, with per-second rates from counter deltas (guarded against restarts).
- Live by default with `L` to pause, `R` to sample now, and `I` to cycle the
  shared refresh interval (5/10/30/60s). All sub-tabs sample continuously on a
  single screen-level timer, so switching sub-tabs never leaves a graph with a
  stale gap. History is session-local and rolling.
- Graphs use a fixed 30-minute time window that fills from the right ("now") to
  the left as history accumulates, with y-axis value labels and an x-axis time
  scale, via a shared framed time-series renderer. The Administration
  Replication tab's lag graph now uses the same renderer and fixed-window
  behavior.

#### Connection Manager

- Connection profiles with environment grouping and backend/vendor detection.
- Credential resolution from profile fields, `.mylogin.cnf` login paths, and
  `.my.cnf` option files.
- SSL and SSH tunnel support.
- Reconnect action (`X` in the Object Browser, `Ctrl+Shift+X` in the SQL
  Workspace). Closes the existing connection and SSH tunnel, re-establishes a
  fresh MySQL session against the current profile, and reloads all metadata.
- Same-endpoint reconnect preserves the SQL Workspace session (editor + log);
  switching to a different profile endpoint rotates the session log and clears
  the editor and results.

#### Object Browser

- Metadata browsing for schemas, tables, views, procedures, functions, events,
  and triggers.
- Per-object tabs: General, Columns, Indexes, Partitions, Foreign Keys,
  Triggers, Grants, Dependencies, DDL, and Sample Data.
- Dependency Analysis Engine using sqlglot to parse procedural SQL and build a
  bidirectional dependency graph with foreign-key labels.

#### SQL Workspace

- Interactive SQL editor with a custom MySQL syntax highlighter covering
  procedural SQL.
- Query execution with typed, colored result output and JSON highlighting.
- EXPLAIN, EXPLAIN FORMAT=JSON, and EXPLAIN ANALYZE.
- Vertical (`\G`) output, horizontal scrolling, and a configurable row display
  limit.
- Session log with owner-only permissions, human-readable durations, and
  save-to-file support.
- Context-aware autocomplete (statement starters, schema objects, and columns
  after a dot), triggered by typing.
- SQL formatter (`Ctrl+Shift+F`) built on sqlglot with configurable rules.

#### Export Framework

- Pluggable, auto-discovered exporters: CSV, CSV (semicolon), TSV,
  SQL INSERT, SQL INSERT (batch), JSONL, JSON, XML, HTML, and Markdown.
- Interactive export (`Ctrl+E`) of the last result set.
- Direct export (`Ctrl+Shift+E`) that streams query results straight to a file.

#### SQL organization and transparency

- Moved substantial application SQL out of Python into `.sql` files under
  `mydba_tui/sql/` (admin, browser/dependency, workspace autocomplete), loaded
  via `load_sql`; trivial statements (SHOW/KILL/SELECT DATABASE, detection
  probes, sample data) remain inline.
- Application-generated statements are tagged with a `/* mydba */` marker so
  they are recognizable in the server process list; user-entered SQL runs
  untouched. File header comments are stripped before statements are sent.
- Connections report `program_name = mydba`, so the tool is identified in the
  process list Program column.
- Autocomplete schema/database values are now escaped before interpolation
  (removing an f-string injection risk).
- The `sql/` directory now lives inside the package and ships with the wheel
  (packaged via `package-data`).

#### Configuration

- Documented `settings.yaml` with human-readable durations.
- `refresh_interval` now drives the Administration live-update cadence, defaults
  to 5 seconds, and is cycled in-app through the fixed choices 5, 10, 30, 60
  (the previous default was 3). Existing config files keep their stored value.

#### Tooling

- `make all` target that runs format, lint, typecheck, test, then the app.

#### Foundation

- Textual TUI application shell, theme support, application and SQL logging,
  and the configuration framework.
- Project documentation set (`docs/`), ADRs, and contribution guidelines.

---

## [0.1.0] - Planned

### Added

- Initial application skeleton.
- Basic Textual application.
- Theme framework.
- Logging framework.
- Configuration framework.
- Connection framework.

---

## [0.2.0] - Planned

### Added

- Connection Manager.
- Connection profiles.
- Environment grouping.
- Backend detection.
- SSL support.
- SSH tunnel support.

---

## [0.3.0] - Planned

### Added

- Object Browser.
- Schema Browser.
- DDL viewer.
- Dependencies.
- Grants.
- Sample data.

---

## [0.4.0] - Planned

### Added

- SQL Workspace.
- Syntax highlighting.
- Query execution.
- Vertical output.
- JSON rendering.
- EXPLAIN support.

---

## [0.5.0] - Planned

### Added

- Administration module.
- Process List.
- Users.
- Replication.
- Variables.
- Status.
- Locks.
- Transactions.

---

## [0.6.0] - Planned

### Added

- Monitoring page.
- Server overview.
- Live metrics.
- Lightweight graphs.

---

## [0.7.0] - Planned

### Added

- Export Framework.
- CSV exporter.
- TSV exporter.
- SQL INSERT exporter.
- JSONL exporter.

---

## [0.8.0] - Planned

### Added

- UI refinements.
- Performance improvements.
- Additional themes.
- Configuration enhancements.

---

## [1.0.0] - Planned

### Added

- First stable release.
- Complete documentation.
- Stable plugin interface.
- Offline installation.
- Cross-platform support.
- Production-ready workflows.

---

## Versioning

The project follows Semantic Versioning:

```
MAJOR.MINOR.PATCH
```

- **MAJOR** — Breaking architectural or API changes.
- **MINOR** — New functionality with backwards compatibility.
- **PATCH** — Bug fixes and minor improvements.

---

## Release Philosophy

Releases should be:

- Small
- Stable
- Well documented
- Fully tested

Every release should provide meaningful improvements while preserving the project's core philosophy of simplicity, transparency, and productivity for professional MySQL DBAs.
