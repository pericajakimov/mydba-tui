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
Workbench does it. On the other paths the Program column is empty.

## Columns

Id, User, Host, db, Command, Time, State, Program, Info.

- Host is shown as the IP/hostname only; the client source port is stripped.
- Time is shown as raw seconds in the table (compact and sortable).
- State and Info are truncated in the table; the full values appear in the
  detail view and when opened in the SQL Workspace.

## Live view and refresh

The list refreshes automatically on an interval (the `refresh_interval`
setting). Auto-refresh can be paused and resumed so a session can be inspected
without the list changing underneath the cursor. The cursor position is
preserved across refreshes by session id.

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
| P | Pause / resume auto-refresh |
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

The Users section displays MySQL accounts grouped into logical categories.

Examples include:

- Administrator users
- Application users
- Read-only users
- Special users

The grouping mechanism is configurable and based on rules defined by the application.

The initial grouping rules are intended for the development team's environments and may be customized later.

The main user list displays only summary information.

Detailed grants are displayed only when the user requests them.

---

# Replication

The Replication section displays replication topology and status.

If the connected server is a primary server:

Display attached replicas.

If the connected server is a replica:

Display information about its replication source together with the most important replication status.

Typical information includes:

- IO Thread
- SQL Thread
- Replication Lag
- Source Server
- Replication State

The presentation should provide immediate operational awareness rather than expose every field returned by `SHOW REPLICA STATUS`.

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

# Locks

The Locks section presents lock information using the most useful views available from the `sys` schema.

The objective is to quickly identify blocking situations without reading raw metadata tables.

---

# Transactions

The Transactions section provides visibility into active database transactions.

Typical information includes:

- Transaction ID
- Connection ID
- User
- Database
- Start Time
- Transaction Age
- Transaction State

The purpose is to help identify long-running or problematic transactions.

---

# Connections

The Connections section presents connection statistics grouped by:

- Username
- Client Host

The client host is displayed as the IP address without the client port.

For each group, the total number of active connections is displayed.

The purpose is to quickly understand connection distribution across applications and users.

---

# Metadata Locks

The Metadata Locks section presents metadata lock information using the most useful views available from the `sys` schema.

The presentation should emphasize blocked objects and blocking sessions.

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

Most operational information is refreshed only when explicitly requested by the
user.

The Process List is an exception: because a live view of active sessions is
genuinely useful, it refreshes automatically on an interval. This auto-refresh
can be paused and resumed at any time, and refreshing can always be triggered
manually.

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