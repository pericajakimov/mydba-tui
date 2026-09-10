# mydba-tui

> A keyboard-first, terminal-native MySQL DBA productivity tool.

---

## Overview

`mydba` is a terminal user interface (TUI) designed for MySQL database administrators who spend most of their time working over SSH on Linux servers or in terminal sessions on their local machines.

The goal of the project is **not** to replace the MySQL client or MySQL Shell, but to extend the existing MySQL ecosystem with a modern, efficient interface that removes repetitive tasks while preserving the familiar DBA workflow.

The tool is intended for daily operational work, troubleshooting, metadata exploration, monitoring, SQL development, and administration of MySQL-compatible databases.

Supported platforms include Oracle MySQL, AWS Aurora MySQL, Percona Server for MySQL, and Percona XtraDB Cluster (PXC), with best-effort compatibility for MariaDB.

---

## Project Goals

- Increase DBA productivity.
- Reduce repetitive typing.
- Provide fast access to metadata.
- Keep the workflow keyboard-first.
- Preserve the look and feel of traditional MySQL tools.
- Remain transparent by never hiding executed SQL.
- Be suitable for offline deployment on secured production environments.

---

## Core Principles

- Metadata-first navigation.
- One application instance = one database connection.
- Human interaction over automation.
- SQL is a first-class citizen.
- Transparent SQL execution.
- Simple, modular architecture.
- Offline installation support.
- Familiar MySQL workflows.
- Minimal learning curve.

---

## Main Features

### Object Browser

Browse MySQL objects without writing metadata queries.

Supported objects include:

- Schemas
- Tables
- Views
- Stored Procedures
- Functions
- Events
- Triggers

For each object, quickly access information such as:

- General information
- DDL
- Columns
- Indexes
- Partitions
- Grants
- Dependencies
- Statistics
- Sample data

---

### SQL Workspace

Integrated SQL editor with:

- Syntax highlighting
- Execute selected text or entire script
- Multiple result sets
- Vertical output similar to `\G`
- Nicely formatted JSON output
- EXPLAIN shortcuts
- Export query results
- SQL session history

---

### Administration

Quick access to operational information including:

- Process List
- Users
- Replication
- Performance (sys schema diagnostics)
- Variables
- Status
- Locks
- Transactions
- Connections
- Metadata Locks
- InnoDB Status

---

### Monitoring

A lightweight live dashboard for operational awareness, organized into sub-tabs
(Overview, InnoDB, Throughput, Locks, Replication). Each is a 2×2 grid of live
braille graphs plus an instant-metrics strip, covering queries/sec, connections,
InnoDB rows and buffer pool, statement mix, network traffic, lock contention,
and replica lag. Graphs use a fixed 30-minute window that fills from the right.
Metrics come from `SHOW GLOBAL STATUS` deltas (one cheap query per tick); live
updates are on by default (`L` pauses, `I` cycles the interval).

This is intentionally **not** a replacement for PMM or Grafana — for detailed,
historical analysis those remain the right tools.

---

### Export Framework

Built-in exporters:

- CSV
- TSV
- SQL INSERT
- JSONL

Designed to support additional exporters through a plugin interface.

---

## Supported Database Platforms

First-class support:

- Oracle MySQL 8.0
- Oracle MySQL 8.4
- AWS Aurora MySQL v3+
- Percona Server for MySQL
- Percona XtraDB Cluster (PXC)

Best-effort support:

- MariaDB

---

## Supported Operating Systems

Development:

- macOS

Deployment:

- Ubuntu 24.04

The project is designed to support offline installation on secured production systems.

---

## Repository Structure

```
docs/
src/            (package code + SQL under src/mydba_tui/sql/)
tests/
scripts/
examples/
packaging/
assets/
```

---

## Development Status

The core interactive workflow is implemented: connecting to a server via
profiles (SSL, SSH tunnel, `.my.cnf` / `.mylogin.cnf`), browsing metadata in
the Object Browser, and writing and running SQL in the SQL Workspace
(highlighting, EXPLAIN, autocomplete, formatting, session logging, and a
pluggable export framework).

Administration is a tabbed screen: a Process List (view active sessions, filter,
kill a query or connection, open a session's query in the SQL Workspace), a
Connections overview (counts grouped by user and host), a Transactions view
(active InnoDB transactions with statement history), InnoDB Locks and Metadata
Locks views (blocking waits with kill-the-blocker), a Users view (accounts
grouped by role with grants on demand), Variables and Status browsers, a
Replication cockpit (role- and vendor-aware, with a live replica-lag graph,
per-channel status, binary logs, GTID, and Galera/PXC state), and a Performance
cockpit over the `sys` schema (top queries, per-user/host activity, waits, I/O,
table and index stats, full scans, and memory — each grid drilling down into
related breakdown views). The live-capable tabs load once and offer opt-in live
updates (`L`) on a configurable, shared refresh interval; all are filterable.
Monitoring is a live dashboard of curated graphs (Overview, InnoDB, Throughput,
Locks, Replication) for a quick "what's happening right now" glance. Polish is
the next area of work. See [`ROADMAP.md`](ROADMAP.md) for the current status of
each milestone.

---

## Project Philosophy

The design philosophy of the project is documented in:

- `docs/00-vision.md`
- `docs/01-philosophy.md`

These documents should be read before contributing to the project.

---

## License

Not yet decided.

---

## Project Status

**Sprint 0 — Architecture & Design**