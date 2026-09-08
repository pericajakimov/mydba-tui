# SQL Browser Queries

This directory contains SQL statements used by the database browser component.

The browser in mydba-tui follows a **metadata-first** approach. Queries in this
directory should retrieve database structure and information required for
navigation, inspection, and administration workflows.

## Purpose

SQL files here are responsible for retrieving metadata such as:

- databases and schemas
- tables
- columns
- indexes
- constraints
- partitions
- views
- stored procedures and functions
- triggers
- events
- storage engine information

## Design Principles

### Metadata over data

The browser should not automatically execute queries against application data
tables.

The default workflow is:

1. Connect to a MySQL server
2. Discover available objects
3. Display metadata
4. Allow the user to explicitly request data operations

### MySQL compatibility

Queries should target standard MySQL metadata sources whenever possible:

- `information_schema`
- `performance_schema`
- `sys` schema

Vendor-specific queries should be isolated and clearly documented.

Examples:

- Aurora MySQL specific queries
- Percona Server specific features
- InnoDB internal diagnostics

## File Naming Convention

SQL files should use descriptive names:
```
<action>_<object>.sql
```
Examples:
- `list_databases.sql`
- `list_tables.sql`
- `show_columns.sql`
- `list_indexes.sql`
- `list_partitions.sql`


## Query Requirements

Each SQL file should:

- contain only SQL
- avoid application-specific formatting
- use named placeholders where parameters are required
- include comments explaining non-obvious logic
- return predictable column names

Example:

```sql
-- List tables for selected schema

SELECT
    table_schema,
    table_name,
    engine,
    table_rows
FROM information_schema.tables
WHERE table_schema = ?
ORDER BY table_name;
```


## Usage

SQL files are loaded by the service layer and executed through the database
connector abstraction.

The UI layer should not execute SQL directly.

Flow:
```
UI
 |
 v
Service
 |
 v
SQL Template
 |
 v
Database Connector
 |
 v
MySQL Server
```

## Future Extensions

This directory may later include:

- version-specific SQL folders
- server capability detection
- generated SQL templates
- explain plan queries
- administration commands