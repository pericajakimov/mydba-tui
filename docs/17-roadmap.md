# Roadmap

## Purpose

This document describes the long-term development roadmap for `mydba`.

The roadmap is intended to guide development priorities while keeping the project focused on its primary objective:

> Build the best terminal-based MySQL administration tool for professional DBAs.

The roadmap is intentionally incremental. Every release should provide useful functionality while maintaining a stable and consistent user experience.

---

# Development Philosophy

Development follows these principles:

- Start small.
- Deliver working software early.
- Avoid over-engineering.
- Build a solid foundation first.
- Add advanced features only when the core experience is complete.

Features should be implemented only after the previous layer is considered stable.

---

# Version 0.1 — Foundation

**Goal:** Establish the project structure and core architecture.

Major deliverables:

- Repository bootstrap
- Project documentation
- Build system
- Application skeleton
- Configuration framework
- Logging framework
- Connection framework
- Initial UI layout
- Theme infrastructure

Outcome:

A running application capable of displaying the basic interface and establishing a MySQL connection.

---

# Version 0.2 — Connection Manager

**Goal:** Make connecting to databases simple and reliable.

Features:

- Connection profiles
- Environment grouping
- Username support
- Password prompting
- Optional `.my.cnf` integration
- Optional `.mylogin.cnf` integration
- SSL support
- SSH tunnel support
- Backend detection
- Connection validation

Outcome:

Reliable connections to supported MySQL servers with automatic platform detection.

---

# Version 0.3 — Object Browser

**Goal:** Replace repetitive metadata queries with intuitive navigation.

Features:

- Schema browser
- Tables
- Views
- Procedures
- Functions
- Events
- Triggers
- Metadata pages
- DDL viewer
- Dependencies
- Grants
- Sample data

Outcome:

The Object Browser becomes the primary way to inspect database objects.

---

# Version 0.4 — SQL Workspace

**Goal:** Provide a modern SQL editing experience inside the terminal.

Features:

- SQL editor
- Syntax highlighting
- F5 execution
- Query history
- Multiple result sets
- Vertical output
- JSON formatting
- Explain support
- Session SQL logging

Outcome:

The SQL Workspace becomes the primary interface for interactive SQL work.

---

# Version 0.5 — Administration

**Goal:** Provide fast access to operational information.

Features:

- Process List
- Users
- Replication
- Variables
- Status
- Transactions
- Locks
- Metadata Locks
- Connections
- InnoDB Status

Outcome:

Routine administrative tasks can be completed without repeatedly writing metadata queries.

---

# Version 0.6 — Monitoring

**Goal:** Provide lightweight operational visibility.

Features:

- Live graphs
- Connections
- Queries per second
- InnoDB reads
- InnoDB writes
- Replication lag
- Operational summary

Outcome:

DBAs gain immediate awareness of server activity without opening external monitoring tools.

---

# Version 0.7 — Export Framework

**Goal:** Make exporting data fast and flexible.

Features:

- CSV
- TSV
- SQL INSERT
- JSONL
- Direct export
- Interactive export
- Streaming exports
- Progress reporting

Outcome:

Efficient export workflows for both small and large result sets.

---

# Version 0.8 — Polish

**Goal:** Improve the overall user experience.

Possible improvements:

- Better keyboard navigation
- Additional themes
- Improved rendering
- Better status indicators
- Performance optimizations
- Error handling improvements
- Additional configuration options

Outcome:

A refined and stable daily-use application.

---

# Version 0.9 — Advanced Features

Potential additions:

- Autocomplete
- SQL snippets
- Saved queries
- Favorite objects
- Advanced filtering
- Search
- Command palette
- Additional exporters
- Enhanced dependency analysis

These features are intentionally postponed until the core workflow is mature.

---

# Version 1.0

**Goal:** Stable public release.

Requirements:

- Stable architecture
- Stable configuration
- Stable plugin API
- Complete documentation
- Comprehensive testing
- Reliable packaging
- Cross-platform support
- Offline installation
- Production readiness

Version 1.0 should be suitable for daily use by professional DBAs.

---

# Future Directions

Possible future work includes:

## Plugin Ecosystem

- Third-party exporters
- Custom monitoring modules
- Utility extensions
- Vendor-specific integrations

---

## Additional Database Platforms

While `mydba` is a MySQL-focused tool, future support may expand to additional MySQL-compatible systems as long as this does not compromise the simplicity of the core architecture.

---

## Server-Specific Enhancements

Examples include:

- Aurora-specific administration
- Percona Server features
- Percona XtraDB Cluster support
- Group Replication support

Server-specific functionality should appear only when supported by the connected server.

---

## Developer Features

Potential future additions:

- SQL autocomplete
- Refactoring tools
- Schema comparison
- Object diff viewer
- Migration helpers

These remain secondary to the project's primary DBA-focused workflow.

---

## Performance Improvements

Future optimization efforts may include:

- Metadata caching
- Background loading
- Lazy rendering
- Parallel metadata retrieval
- Incremental UI updates

Performance optimizations should always preserve correctness and maintainability.

---

# What Is Not Planned

The following are intentionally outside the current project scope:

- Replacing PMM or Grafana
- Full database IDE functionality
- Automated deployment pipelines
- Schema migration frameworks
- General-purpose automation platform
- Multi-database abstraction layers

`mydba` is an interactive DBA tool, not an automation framework.

---

# Long-Term Vision

The long-term goal is for experienced MySQL DBAs to feel immediately productive when using `mydba`.

The application should feel like a natural extension of the existing MySQL command-line ecosystem while providing a significantly better interactive experience for everyday administration.

---

# Design Principles

The roadmap follows these principles:

- Build the foundation first.
- Deliver usable functionality early.
- Prioritize DBA workflows.
- Keep the architecture extensible.
- Prefer refinement over feature accumulation.
- Maintain simplicity as the project grows.
