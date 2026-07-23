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

A persistent header showing `schema.table` is displayed above the tabs, visible regardless of which tab is active.

Available tabs:

- General
- Columns
- Indexes
- Partitions
- Foreign Keys
- Triggers
- Grants
- DDL
- Events
- Dependencies
- Sample Data

---

# General Information

General Information provides a concise overview of the table.

Displayed fields include:

- Storage engine
- Row format
- Row count (approximate)
- Average row length
- Data size
- Index size
- Total size
- Free space
- Fragmentation percentage
- Auto increment value
- Collation
- Create options
- Creation time
- Last update time
- Last checked time
- Comment

The goal is to quickly determine the overall state of the table without reading the DDL.

---

# DDL

The DDL view displays the output of `SHOW CREATE TABLE`.

Requirements:

- Proper indentation.
- Scrollable.
- Easy to read.

The displayed SQL should closely resemble the output produced by `mysqldump`.

Syntax highlighting will be added in a future iteration as a unified feature across all SQL-displaying views.

---

# Columns

The Columns view displays:

- Position
- Column name
- Data type
- Nullable
- Key type (PRI, UNI, MUL)
- Default value
- Extra (auto_increment, etc.)

Information already obvious from the DDL is intentionally omitted from the default view.

Examples of omitted fields:

- Character set
- Collation
- Comments

These remain available in the DDL when needed.

---

# Indexes

The Indexes view displays:

- Index name (PRIMARY highlighted, UNIQUE indicated)
- Columns (including functional expressions)
- Index type (BTREE, HASH, FULLTEXT, SPATIAL)
- Cardinality with selectivity percentage
- Low selectivity warning for non-primary indexes
- Visibility (INVISIBLE flag when applicable)
- Size per index (from `mysql.innodb_index_stats`, when available)
- Comment

Indexes are grouped by name with PRIMARY listed first. The purpose is to provide a quick overview of index design and usefulness.

---

# Partitions

The Partitions view displays information obtained from `information_schema.partitions`.

Non-partitioned tables display "Table is not partitioned."

For partitioned tables, the view shows:

Header (table-level):

- Partition method (RANGE, LIST, HASH, KEY)
- Partition expression

Tabular per-partition details:

- Partition name
- Description (range boundary or list values)
- Row count
- Data size
- Index size
- Total size

This view should provide enough information for operational troubleshooting without requiring manual metadata queries.

---

# Foreign Keys

The Foreign Keys view displays two sections:

**References** (outgoing): FK constraints defined on this table pointing to other tables.

**Referenced By** (incoming): FK constraints from other tables pointing to this table.

Each foreign key is displayed as:

- Arrow summary line showing column mapping (e.g., `customer_id → customers(id)`)
- Dimmed multi-line DDL-style declaration (CONSTRAINT, FOREIGN KEY, REFERENCES, ON DELETE/UPDATE rules)

Multi-column foreign keys show all columns on one line.

Note: MySQL does not support cross-schema foreign keys, so schema names are omitted.

---

# Triggers

Displays all triggers defined for the table.

For each trigger:

- Name (bold cyan)
- Event (INSERT, UPDATE, DELETE)
- Timing (BEFORE, AFTER)
- Definer
- Creation timestamp
- SQL body (raw text)

Multiple triggers are separated by a horizontal line.

Syntax highlighting for the body will be added in a future iteration.

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

Status: Not yet implemented.

---

# Dependencies

The Dependencies view will provide object relationships determined by combining metadata and object definitions.

Hard-wired dependencies (from metadata):

- Foreign keys referencing this table (already shown in the Foreign Keys tab under "Referenced By").

Code-based dependencies (text search in definitions):

- Views using the table.
- Procedures using the table.
- Functions using the table.
- Triggers referencing the table in their body.
- Events using the table.

Code-based dependencies are best-effort (text matching in definitions) and will be clearly indicated as such.

Status: Planned for a future iteration as a separate tab.

---

# Events (Future)

The Events tab displays scheduled events associated with the table's schema that reference this table.

For each event:

- Name
- Type (ONE TIME, RECURRING)
- Schedule (interval/timing)
- Status (ENABLED, DISABLED, SLAVESIDE_DISABLED)
- Definer
- SQL body

Syntax highlighting for the body will be added in a future iteration alongside other SQL-displaying views.

Status: Not yet implemented.

---

# Sample Data (Future)

Sample Data is optional and never loaded automatically.

The tab provides two actions:

- **First rows** — executes `SELECT * FROM table ORDER BY <pk> ASC LIMIT N`
- **Last rows** — executes `SELECT * FROM table ORDER BY <pk> DESC LIMIT N`

Default limit: 10 rows. The limit will be configurable.

The purpose is only to quickly verify how data inside the table looks. For advanced querying, the SQL Workspace module is available.

Results are displayed in a tabular format with column headers.

Status: Not yet implemented.

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
