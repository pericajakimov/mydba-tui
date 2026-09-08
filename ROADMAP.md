# mydba Roadmap

This document provides a high-level overview of the planned evolution of **mydba**.

Detailed implementation plans are documented in `docs/17-roadmap.md`. This file serves as a quick reference for contributors and users.

---

# Vision

The long-term goal of `mydba` is:

> Build the best terminal-based MySQL administration tool for professional MySQL DBAs.

The project focuses on making experienced DBAs more productive through a fast, keyboard-first, metadata-first terminal interface.

---

# Current Status

**Project Phase:** Active development

The core interactive workflow is implemented. A DBA can connect to a server,
browse metadata, and write and run SQL end to end.

Implemented:

- Foundation — TUI application, logging, configuration, theme support
- Connection Manager — profiles, environment grouping, backend detection,
  `.my.cnf` / `.mylogin.cnf`, SSL, SSH tunnel, explicit Reconnect
- Object Browser — schemas, tables, views, routines, events, triggers, DDL,
  dependencies, grants, sample data
- SQL Workspace — editor, MySQL syntax highlighting, execution, EXPLAIN,
  vertical output, JSON rendering, session logging, autocomplete, formatter
- Export Framework — pluggable, auto-discovered exporters (CSV, CSV-semicolon,
  TSV, SQL INSERT/batch, JSONL, JSON, XML, HTML, Markdown), interactive and
  streaming direct export

In progress / next:

- Administration — tabbed screen with Process List (live, filterable, kill
  sessions, open query in workspace), Connections (grouped counts), Variables,
  and Status; Transactions, Locks, Users, Replication next
- Monitoring (server activity, live metrics, lightweight graphs)
- Polish (performance, rendering, error handling, additional themes)

---

# Milestones

## Milestone 1 — Foundation ✅ Done

- Repository bootstrap
- Project documentation
- Build system
- Logging framework
- Configuration framework
- Basic TUI application
- Theme support

---

## Milestone 2 — Connection Manager ✅ Done

- Connection profiles
- Environment grouping
- Backend detection
- `.my.cnf` integration
- `.mylogin.cnf` integration
- SSL support
- SSH tunnel support
- Reconnect

---

## Milestone 3 — Object Browser ✅ Done

- Schemas
- Tables
- Views
- Procedures
- Functions
- Events
- Triggers
- DDL viewer
- Dependencies
- Grants
- Sample data

---

## Milestone 4 — SQL Workspace ✅ Done

- SQL editor
- Syntax highlighting
- Query execution
- Result history
- Vertical output
- JSON rendering
- EXPLAIN support
- SQL logging
- SQL autocomplete
- SQL formatter

---

## Milestone 5 — Administration 🚧 In progress

- Process List ✅
- Connections ✅
- Variables ✅
- Status ✅
- Users
- Replication
- Transactions
- Locks
- Metadata Locks
- InnoDB Status
- Connection statistics

---

## Milestone 6 — Monitoring 🔜 Next

- Server activity overview
- Connection usage
- Queries per second
- InnoDB reads/writes
- Replication lag
- Lightweight graphs

---

## Milestone 7 — Export Framework ✅ Done

- CSV (comma and semicolon)
- TSV
- SQL INSERT (single and batch)
- JSONL
- JSON
- XML
- HTML
- Markdown
- Streaming (direct) exports
- Plugin-based, auto-discovered exporter interface

---

## Milestone 8 — Polish 🔜 Planned

- UI improvements
- Performance tuning
- Better rendering
- Error handling refinements
- Additional themes
- Configuration enhancements

---

## Version 1.0

The first stable release will include:

- Stable architecture
- Stable configuration
- Stable plugin interface
- Cross-platform support
- Offline installation
- Complete documentation
- Production-ready workflows

---

# Future Ideas

Potential future enhancements include:

- Search
- Command palette
- Query history across sessions
- Additional exporters (Excel, Parquet, compressed output)
- Advanced dependency analysis
- Vendor-specific plugins
- Performance improvements

These features are intentionally deferred until the core workflow is complete.

---

# Out of Scope

The project does **not** aim to become:

- A full database IDE
- A monitoring platform
- A deployment tool
- A migration framework
- An automation platform

Its focus remains interactive MySQL database administration.

---

# Guiding Principle

Every new feature should answer one question:

> **Does this make a professional MySQL DBA faster and more effective during day-to-day work?**

If the answer is **yes**, it belongs in `mydba`.

If not, it should be reconsidered or postponed.
