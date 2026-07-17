# SQL Workspace Queries

This directory contains SQL statements used by the SQL workspace component.

The SQL workspace provides an interactive environment for writing, executing,
and analyzing SQL statements while keeping execution separate from the UI
layer.

## Purpose

SQL files here support:

- query execution helpers
- SQL history operations
- query analysis
- execution plan retrieval
- session information
- result metadata handling
- administrative SQL templates

## Design Principles

### Explicit execution

The SQL workspace should never execute SQL automatically.

The user must explicitly:

1. Write or select SQL
2. Review the statement
3. Execute the statement
4. Review the result

### Separation of concerns

SQL execution flow:
```
User
|
v
SQL Workspace UI
|
v
SQL Service
|
v
Database Connector
|
v
MySQL Server
```
The UI layer should not contain SQL execution logic.

### Safe defaults

The workspace should support DBA workflows while avoiding accidental changes.

Future safety features:

- read-only mode
- confirmation prompts for DDL/DML
- transaction awareness
- query classification
- execution timeout controls

## File Naming Convention

SQL files should use descriptive names:
```
<action>_<purpose>.sql
```

Examples:
- `explain_query.sql`
- `show_session_status.sql`
- `get_execution_plan.sql`
- `list_query_history.sql`


## Query Requirements

Each SQL file should:

- contain only SQL
- avoid UI-specific formatting
- use placeholders for dynamic values
- include comments for complex logic
- return predictable column names

Example:

```sql
-- Retrieve execution plan for a query

EXPLAIN FORMAT=JSON
SELECT
    *
FROM
    table_name
WHERE
    id = ?;
```

## Query Categories

Future SQL files may be organized into:

```
workspace/
├── explain/
├── execution/
├── history/
├── session/
└── diagnostics/
```

## MySQL Compatibility

Queries should support standard MySQL behavior whenever possible.

Vendor-specific SQL should be isolated and documented:

- Aurora MySQL extensions
- Percona Server features
- MySQL Enterprise features


## Future Extensions

This directory may later include:

- SQL formatter integration
- query plan visualization queries
- EXPLAIN ANALYZE helpers
- query cost comparison
- saved DBA scripts
- migration helpers
- generated administrative statements
