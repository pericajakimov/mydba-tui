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

The Process List provides a live view of active MySQL sessions.

The view should support dynamic filtering.

Typical filters include:

- Active connections only
- Sleeping connections
- Username
- Host
- Database
- Command
- State

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

The Variables section provides access to MySQL global variables.

The preferred initial view displays only variables whose values differ from the server defaults.

If supported by the implementation, the user may switch to viewing all variables.

Dynamic filtering by variable name and value should be available.

---

# Status

The Status section provides access to global status counters.

Dynamic filtering should allow quick location of individual status values.

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

Operational information should be refreshed only when explicitly requested by the user.

The Administration module does not perform automatic background refreshes.

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