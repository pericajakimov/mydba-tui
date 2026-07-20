# Architecture

## Overview

`mydba` is designed as a modular, keyboard-first terminal application for MySQL database administration.

The architecture prioritizes:

- Simplicity
- Maintainability
- Clear module boundaries
- Extensibility
- Transparency

Every module has a single responsibility and communicates with other modules through well-defined interfaces.

---

# High-Level Architecture

```
+--------------------------------------------------------------+
|                          Textual UI                          |
|                                                              |
|  Header   Footer   Navigation   Screens   Dialogs   Widgets  |
+-------------------------------+------------------------------+
                                |
                                v
+--------------------------------------------------------------+
|                     Application Controller                   |
+-------------------------------+------------------------------+
                                |
        +-----------+-----------+-----------+-----------+
        |           |           |           |           |
        v           v           v           v           v
   Browser     Workspace   Administration Monitoring Connection
     Module       Module        Module        Module     Module
        |           |             |             |          |
        +-----------+-------------+-------------+----------+
                                |
                                v
+--------------------------------------------------------------+
|                       Service Layer                          |
+--------------------------------------------------------------+
                                |
                                v
+--------------------------------------------------------------+
|                     MySQL Connector Driver                   |
+--------------------------------------------------------------+
                                |
                                v
                        MySQL Compatible Server
```

---

# Design Principles

The architecture follows these principles:

- One responsibility per module.
- Loose coupling.
- High cohesion.
- SQL separated from business logic whenever practical.
- UI independent from database implementation.
- Keyboard-first interaction.
- Metadata-first workflow.

---

# Application Layers

## Presentation Layer

Responsible for:

- Rendering the user interface.
- Keyboard handling.
- Screen navigation.
- Dialogs.
- User interaction.

The presentation layer never contains database logic.

---

## Application Layer

Responsible for:

- Coordinating workflows.
- Handling user actions.
- Calling services.
- Managing screen state.

This layer connects the UI with the service layer.

---

## Service Layer

Responsible for:

- Executing SQL.
- Loading metadata.
- Server detection.
- Object inspection.
- Monitoring.
- Export operations.

Business logic belongs here.

---

## Data Access Layer

Responsible for communication with MySQL.

Responsibilities include:

- Opening connections.
- Executing statements.
- Returning results.
- Transaction handling.
- Error propagation.

The rest of the application should never communicate directly with the database driver.

---

# Main Modules

## Connection Manager

Responsible for:

- Profile management.
- Authentication.
- Connection establishment.
- Server capability detection.
- SSL handling.
- SSH tunnel support.

---

## Object Browser

Responsible for browsing database metadata.

Supported objects include:

- Schemas
- Tables
- Views
- Stored Procedures
- Functions
- Events
- Triggers

The Browser never loads table data automatically.

---

## SQL Workspace

Provides an integrated SQL editor.

Responsibilities:

- SQL editing.
- SQL execution.
- Result rendering.
- Query history.
- EXPLAIN support.
- Result exporting.

---

## Administration

Provides operational information about the server.

Examples include:

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

## Monitoring

Provides lightweight live monitoring.

Designed for operational awareness rather than detailed performance analysis.

---

## Export Framework

Provides a common interface for exporting result sets.

Initial exporters:

- CSV
- TSV
- SQL INSERT
- JSONL

---

## Rendering Engine

Responsible for formatting:

- SQL
- JSON
- Result sets
- Vertical output
- Metadata tables

Rendering rules remain independent of the modules producing the data.

---

# Package Organization

```
src/mydba_tui/

    app.py

    browser/
    config/
    connection/
    exporters/
    logging/
    models/
    monitoring/
    renderers/
    server/
    services/
    sql/
    themes/
    ui/
    utils/
    workspace/
```

Each package has a clearly defined responsibility.

---

# SQL Organization

Whenever practical, SQL statements are stored as standalone SQL files.

Example:

```
sql/

    browser/
    server/
    monitoring/
    admin/
    workspace/
```

Benefits include:

- Easier review.
- Easier optimization.
- Better collaboration between developers and DBAs.
- Cleaner Python code.

Dynamic SQL should only be generated when required.

---

# Logging

Two independent logging systems exist.

## Application Log

Contains:

- Internal events.
- Python logging.
- Exceptions.
- Debug information.

## SQL Log

Contains every SQL statement executed against the server.

This includes:

- User SQL.
- Metadata queries.
- Monitoring queries.
- Internal Browser queries.

Each entry records:

- Timestamp.
- Execution duration.
- Source module (e.g. `browser.tables`, `server.detection`, `workspace.execute`).
- SQL text collapsed to a single line.

Multi-line SQL from `.sql` files is collapsed into one line for grep-friendly log output.

The SQL log never contains Python logging messages.

---

# Connection Model

One running application instance owns exactly one database connection.

Changing the connection requires starting a new application session.

Multiple simultaneous database connections are achieved by running multiple application instances.

---

# Server Detection

After connecting, the application detects the server capabilities.

Examples include:

- Oracle MySQL
- AWS Aurora
- Percona Server
- Percona XtraDB Cluster
- MariaDB

Features presented to the user depend on detected capabilities.

---

# Configuration

Configuration is divided into:

- Application settings.
- Connection profiles.
- Theme settings.

Configuration should remain human-readable whenever practical.

---

# Extensibility

The architecture should allow future expansion without changing existing modules.

Examples include:

- New exporters.
- Additional monitoring pages.
- New object inspectors.
- Optional MySQL Shell integration.

Future functionality should be added through new modules rather than modifying unrelated components.

---

# Guiding Principle

The architecture should remain understandable to both Python developers and experienced MySQL DBAs.

Every major component should have a clear purpose, minimal dependencies, and a well-defined responsibility.
