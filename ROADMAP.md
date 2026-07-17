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

**Project Phase:** Bootstrap

Current work focuses on:

- Project architecture
- Documentation
- Repository structure
- Development environment
- Core framework

No functional features have been implemented yet.

---

# Milestones

## Milestone 1 — Foundation

- Repository bootstrap
- Project documentation
- Build system
- Logging framework
- Configuration framework
- Basic TUI application
- Theme support

---

## Milestone 2 — Connection Manager

- Connection profiles
- Environment grouping
- Backend detection
- `.my.cnf` integration
- `.mylogin.cnf` integration
- SSL support
- SSH tunnel support

---

## Milestone 3 — Object Browser

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

## Milestone 4 — SQL Workspace

- SQL editor
- Syntax highlighting
- Query execution
- Result history
- Vertical output
- JSON rendering
- EXPLAIN support
- SQL logging

---

## Milestone 5 — Administration

- Process List
- Users
- Replication
- Variables
- Status
- Transactions
- Locks
- Metadata Locks
- InnoDB Status
- Connection statistics

---

## Milestone 6 — Monitoring

- Server activity overview
- Connection usage
- Queries per second
- InnoDB reads/writes
- Replication lag
- Lightweight graphs

---

## Milestone 7 — Export Framework

- CSV
- TSV
- SQL INSERT
- JSONL
- Streaming exports
- Progress reporting
- Plugin-based exporter interface

---

## Milestone 8 — Polish

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

- SQL autocomplete
- Search
- Command palette
- Additional exporters
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
