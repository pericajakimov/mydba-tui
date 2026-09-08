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
- Variables
- Status
- Locks
- Transactions
- Connections
- Metadata Locks
- InnoDB Status

---

### Monitoring

Lightweight live monitoring designed for operational awareness.

Examples:

- Queries per second
- Connections
- InnoDB reads
- InnoDB writes
- Replication lag

This is intentionally **not** a replacement for PMM or Grafana.

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
src/
sql/
tests/
scripts/
themes/
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

Administration, Monitoring, and polish are the next areas of work. See
[`ROADMAP.md`](ROADMAP.md) for the current status of each milestone.

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