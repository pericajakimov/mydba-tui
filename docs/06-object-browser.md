# Object Browser

## Purpose

The Object Browser provides fast, keyboard-driven access to MySQL database objects and their metadata.

Its primary objective is to eliminate repetitive metadata queries while preserving complete transparency about the information being presented.

The Object Browser is intended for inspection, understanding and navigation of database objects. It is **not** intended for browsing table data by default.

---

# Design Goals

The Object Browser should:

- Be metadata-first.
- Load information quickly.
- Avoid unnecessary SQL.
- Require minimal typing.
- Present information in a consistent layout.
- Support large databases.
- Never execute expensive operations automatically.

---

# Supported Object Types

The Browser supports:

- Schemas
- Tables
- Views
- Stored Procedures
- Functions
- Events
- Triggers

Future object types may be added without changing the navigation model.

---

# Layout

The Object Browser uses a split-pane layout:

```
+------------------------------------------------------------------+
| Header                                                           |
+------------------------------------------------------------------+
| Status Bar (connection info)                                     |
+------------------------------------------------------------------+
|              |                                                    |
| Browser Tree |          Content / Working Area                   |
| (schemas,    |                                                    |
|  objects)    |   (metadata, DDL, SQL results)                    |
|              |                                                    |
|              |                                                    |
+------------------------------------------------------------------+
| Footer (key bindings)                                            |
+------------------------------------------------------------------+
```

The left panel contains the tree-style object browser (always visible).
The right panel shows metadata for the selected object or SQL workspace.

The browser panel remains visible while navigating between objects
and while using the SQL workspace.

---

# Navigation

The Browser follows a hierarchical tree structure.

```
Schemas

    sales
        Tables (42)
        Views (3)
        Procedures (7)
        Functions (2)
        Events (1)
        Triggers (5)

    reporting
        ...

    mysql
        ...

    sys
        ...
```

Selecting an object opens its metadata view.

No table data is loaded automatically.

Object counts are displayed next to each category name. Schema contents
are loaded lazily — only when a schema node is expanded for the first time.
Individual objects within a category are also loaded lazily on expansion.

---

# Metadata-First Philosophy

Selecting an object should answer:

> "What is this object?"

rather than

> "What data does it contain?"

Sample data is always an explicit user action.

---

# Table View

The Table View provides quick access to the most useful administrative information.

Available sections:

- General Information
- DDL
- Columns
- Indexes
- Partitions
- Statistics
- Triggers
- Sample Data
- Grants
- Dependencies

---

# General Information

General Information provides a concise overview of the table.

Displayed fields include:

- Storage engine
- Row count
- Data size
- Index size
- Total size
- Free space
- Fragmentation percentage
- Creation time
- Last update time

The goal is to quickly determine the overall state of the table without reading the DDL.

---

# DDL

The DDL view displays the output of `SHOW CREATE TABLE`.

Requirements:

- Syntax highlighted.
- Proper indentation.
- Scrollable.
- Easy to read.

The displayed SQL should closely resemble the output produced by `mysqldump`.

---

# Columns

The Columns view displays:

- Column name
- Data type
- Nullable
- Default value

Information already obvious from the DDL is intentionally omitted.

Examples:

- Character set
- Collation
- Comments
- Extra attributes

These remain available in the DDL when needed.

---

# Indexes

The Indexes view displays:

- Index name
- Columns
- Index type
- Cardinality
- Size (where available)

The purpose is to provide a quick overview of index design and usefulness.

---

# Partitions

The Partitions view displays information obtained from `information_schema.partitions`.

Examples include:

- Partition name
- Partition method
- Partition expression
- Row count
- Data size
- Index size

This view should provide enough information for operational troubleshooting without requiring manual metadata queries.

---

# Statistics

The Statistics view presents operational information useful for understanding table behavior.

Potential sources include:

- `sys` schema
- Performance Schema
- Other server metadata

Examples include:

- I/O statistics
- Wait statistics

The exact contents may evolve over time.

---

# Triggers

Displays all triggers defined for the table.

For each trigger:

- Name
- Event
- Timing
- SQL definition

The SQL definition is syntax highlighted.

---

# Sample Data

Sample Data is optional.

It is never loaded automatically.

When requested, the Browser executes a simple query returning a small number of rows from the table.

Typical limit:

- 5 rows
- 10 rows

The purpose is only to verify table contents.

---

# Grants

Displays only the privileges that actually exist for the selected object.

Example:

```
user1

    SELECT

user2

    ALL

user3

    SELECT
    INSERT
    UPDATE
    DELETE
```

The goal is to provide an immediate understanding of object access without reading multiple `SHOW GRANTS` statements.

---

# Dependencies

The Dependencies view provides object relationships.

Examples include:

Incoming dependencies:

- Foreign keys referencing this table.

Outgoing dependencies:

- Views using the table.
- Procedures using the table.
- Functions using the table.
- Triggers using the table.
- Events using the table.

Dependencies are determined by combining metadata and object definitions where appropriate.

---

# View Browser

For Views, the Browser provides:

- SQL Definition
- Columns
- Grants
- Dependencies
- Updatable status

The SQL definition is syntax highlighted and formatted for readability.

Columns display the resolved data types, making the structure easier to understand than reading the SQL alone.

---

# Stored Procedures

For Stored Procedures, the Browser provides:

- Source code
- Grants
- Call hierarchy
- Dependencies

The source code is displayed with syntax highlighting and proper formatting.

Parameter information is intentionally omitted because it is already present in the DDL.

---

# Functions

The Function view behaves identically to the Procedure view.

Available sections:

- Source code
- Grants
- Call hierarchy
- Dependencies

---

# Events

For Events, the Browser provides:

- SQL definition
- General information
- Dependencies

General information is obtained from `SHOW EVENTS`.

---

# Triggers

When browsing triggers directly, the Browser displays:

- SQL definition
- Event
- Timing
- Target table

The SQL definition is syntax highlighted.

---

# Object Loading

Metadata should be loaded only when required.

Selecting one object should never trigger loading metadata for unrelated objects.

This keeps navigation responsive even on large servers.

---

# SQL Transparency

All metadata queries executed by the Browser are recorded in the SQL log.

The Browser never hides the SQL used to obtain its information.

---

# Design Principles

The Object Browser follows these principles:

- Metadata before data.
- Fast navigation.
- Readable presentation.
- Consistent layouts.
- Explicit loading of expensive operations.
- Familiar MySQL terminology.
- Complete SQL transparency.
