# SQL Administration Queries

This directory contains SQL statements used for database administration tasks
performed by mydba-tui.

The queries in this directory support common DBA operations while keeping
administrative actions organized and separated from monitoring and browsing
functionality.

## Purpose

SQL files here contain administrative operations such as:

- user and privilege management
- database object maintenance
- schema administration
- table maintenance
- configuration changes
- operational commands
- database health actions

## Design Principles

### Explicit DBA actions

Administrative operations should always require explicit user action.

The application should:

1. Display the requested operation
2. Show the generated SQL
3. Require confirmation when appropriate
4. Execute only after user approval

### Safety first

Administrative SQL can affect production systems.

Future safety mechanisms:

- read-only mode
- environment awareness
- production execution warnings
- privilege checks
- SQL preview before execution
- audit logging

## SQL Categories

Administrative queries may include:

### User Management

Examples:

- create users
- alter users
- grant privileges
- revoke privileges
- inspect permissions

### Object Maintenance

Examples:

- analyze tables
- optimize tables
- check tables
- repair tables where supported

### Schema Operations

Examples:

- create database
- alter objects
- generate DDL
- inspect dependencies

### Operational Commands

Examples:

- flush operations
- session management
- configuration changes

## File Naming Convention

SQL files should use descriptive names:
```
<action>_<object>.sql
```

Examples:
- `create_user.sql`
- `grant_privileges.sql`
- `analyze_table.sql`
- `check_table.sql`
- `generate_table_ddl.sql`


## Query Requirements

Each SQL file should:

- contain only SQL
- include comments explaining the operation
- document required privileges
- use parameters where possible
- avoid destructive actions without confirmation
- return predictable output

Example:

```sql
-- Analyze table statistics
-- Required privilege: TABLE ADMIN or equivalent

ANALYZE TABLE
    ?;
```

## Dangerous Operations

The following operations require additional protection:

- `DROP`
- `TRUNCATE`
- `DELETE`
- `ALTER TABLE`
- privilege escalation
- account removal
- configuration changes

These operations should:

- display a warning
- require confirmation
- log the executed statement

## Usage

Administrative SQL is executed through the service layer.

The UI layer should never directly execute administrative SQL.

Flow:
```
UI
 |
 v
Administration Service
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

## Server Compatibility

Administrative features depend on the detected server type.

Examples:

- MySQL Community Server
- Percona Server
- AWS Aurora MySQL

Vendor-specific administrative SQL should be isolated and documented.

## Future Extensions

This directory may later include:

- generated DDL statements
- online schema change helpers
- migration utilities
- backup and restore helpers
- user permission reports
- security auditing queries
- replication administration tools