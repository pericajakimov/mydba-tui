# Decision Log

## Purpose

This document records architectural and design decisions made throughout the development of `mydba`.

The purpose is to preserve the reasoning behind important decisions so they are not revisited unnecessarily and future contributors understand why specific approaches were chosen.

This document is append-only. Decisions should never be modified after implementation. If a decision changes, a new entry should be added explaining the new direction.

---

# Decision Format

Each decision follows the same structure:

- ID
- Date
- Status
- Decision
- Rationale

Status values:

- Accepted
- Superseded
- Deprecated

---

# MDBA-0001

**Status:** Accepted

## Decision

The project is a terminal user interface (TUI) application built using the Textual framework.

## Rationale

The target users work primarily over SSH on Linux tooling servers. A TUI provides a significantly better user experience than the traditional MySQL client while remaining lightweight and terminal-native.

---

# MDBA-0002

**Status:** Accepted

## Decision

The application uses the standard Python MySQL driver instead of MySQL Shell.

## Rationale

The Python driver provides everything required for the initial implementation while reducing complexity and external dependencies.

Future MySQL Shell integration, such as dump utilities, may be implemented as an optional plugin or module.

---

# MDBA-0003

**Status:** Accepted

## Decision

Official Linux releases are built on Ubuntu.

## Rationale

Development takes place primarily on macOS, but release artifacts should be built on the target operating system to maximize compatibility with production tooling servers.

---

# MDBA-0004

**Status:** Accepted

## Decision

The project naming is:

- Repository: `mydba-tui`
- Python package: `mydba_tui`
- Executable: `mydba`

## Rationale

This naming clearly separates the repository, Python package, and installed executable while keeping the command users type short and memorable.

---

# MDBA-0005

**Status:** Accepted

## Decision

`mydba` is a MySQL administration tool, not an Aurora administration tool.

## Rationale

The application should support Oracle MySQL, AWS Aurora, Percona Server, and Percona XtraDB Cluster.

Server-specific functionality is enabled automatically only when supported by the connected server.

---

# MDBA-0006

**Status:** Accepted

## Decision

Metadata-first navigation is preferred over data-first navigation.

## Rationale

DBAs spend far more time inspecting metadata than browsing table contents.

The Object Browser should therefore present metadata immediately, while actions such as viewing sample data remain explicit user actions.

---

# MDBA-0007

**Status:** Accepted

## Decision

The primary navigation model is keyboard-driven using function keys.

## Rationale

Professional DBAs spend long periods in terminal sessions.

Function keys are easy to discover, easy to document in the UI, and avoid complex keyboard shortcuts that are difficult to remember.

---

# MDBA-0008

**Status:** Accepted

## Decision

The application should always display a visible navigation guide.

## Rationale

Users should never need to memorize keyboard shortcuts.

Available actions should always be visible on screen.

---

# MDBA-0009

**Status:** Accepted

## Decision

The SQL Workspace follows the execution model of SQL Server Management Studio.

## Rationale

- F5 executes SQL.
- If text is selected, execute only the selection.
- Otherwise execute the entire editor contents.

This behavior is familiar, predictable, and efficient.

---

# MDBA-0010

**Status:** Accepted

## Decision

Vertical query output should follow the style of the MySQL client (`\G`).

## Rationale

Professional MySQL DBAs are already familiar with this format.

Field names remain right-aligned before the separator, while JSON values receive enhanced formatting and syntax highlighting.

---

# MDBA-0011

**Status:** Accepted

## Decision

JSON values are automatically formatted when displayed.

## Rationale

Indented, syntax-highlighted JSON is significantly easier to inspect than compact one-line JSON documents.

---

# MDBA-0012

**Status:** Accepted

## Decision

Connection profiles represent endpoints rather than users.

## Rationale

A profile primarily identifies a database endpoint.

Usernames may optionally be stored with the profile, but passwords should normally be entered at connection time.

---

# MDBA-0013

**Status:** Accepted

## Decision

Passwords are not stored by default.

## Rationale

Most production deployments use shared tooling servers.

Avoiding stored passwords minimizes credential exposure while remaining compatible with existing MySQL credential mechanisms.

---

# MDBA-0014

**Status:** Accepted

## Decision

The application integrates with existing MySQL credential files.

## Rationale

When available, `.my.cnf` and `.mylogin.cnf` should be reusable to preserve compatibility with the existing MySQL ecosystem.

---

# MDBA-0015

**Status:** Accepted

## Decision

The active environment is always visible in the application header.

## Rationale

Production mistakes are often caused by losing awareness of the connected environment.

Persistent environment indicators reduce this risk.

---

# MDBA-0016

**Status:** Accepted

## Decision

Environment colors are defined by connection profiles.

## Rationale

Recommended mapping:

- Production → Red
- Stage → Orange
- QA → Blue
- Development → Green

This provides immediate visual context.

---

# MDBA-0017

**Status:** Accepted

## Decision

Monitoring is intentionally lightweight.

## Rationale

Detailed performance analysis belongs in dedicated monitoring platforms such as PMM.

`mydba` focuses on providing a quick operational overview.

---

# MDBA-0018

**Status:** Accepted

## Decision

Every SQL statement generated by the application is logged.

## Rationale

The SQL log allows DBAs to understand exactly how the application retrieves metadata and operational information, making behavior transparent and simplifying optimization.

The SQL log contains only SQL statements.

---

# MDBA-0019

**Status:** Accepted

## Decision

Application logs and SQL logs are stored separately.

## Rationale

Operational debugging and SQL transparency serve different purposes and should not be mixed.

---

# MDBA-0020

**Status:** Accepted

## Decision

Each `mydba` instance owns exactly one database connection.

## Rationale

Working with multiple servers is achieved by running multiple application instances.

This mirrors the workflow of the standard MySQL client and avoids confusion between active sessions.

---

# MDBA-0021

**Status:** Accepted

## Decision

The Export Framework is plugin-based.

## Rationale

The initial release supports CSV, TSV, SQL INSERT, and JSONL while allowing additional export formats to be added without modifying the core application.

---

# MDBA-0022

**Status:** Accepted

## Decision

Long-running exports stream rows directly to the destination file.

## Rationale

Streaming minimizes memory usage and enables exporting very large result sets.

---

# MDBA-0023

**Status:** Accepted

## Decision

The project prioritizes familiarity over novelty.

## Rationale

Professional MySQL DBAs should feel immediately comfortable using `mydba`.

The application should behave like a natural extension of the existing MySQL command-line ecosystem rather than introducing entirely new interaction models.

---

# Future Decisions

New architectural decisions should be appended to this document as development progresses.

Existing accepted decisions should remain unchanged to preserve the historical evolution of the project.
