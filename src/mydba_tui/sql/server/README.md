# SQL Server Queries

This directory contains SQL statements used for MySQL server discovery,
capability detection, and server-level information retrieval.

The queries in this directory support the server information and connection
workflow of mydba-tui.

## Purpose

SQL files here retrieve information about the MySQL server instance, including:

- server version
- edition and vendor information
- available features
- configuration variables
- server status
- storage engines
- system capabilities
- replication capabilities
- cloud-provider-specific features

## Design Principles

### Server detection first

Before enabling advanced functionality, mydba-tui should detect the connected
server capabilities.

Examples:

- MySQL Community Server
- MySQL Enterprise Server
- Percona Server
- AWS Aurora MySQL

The application should enable features based on detected capabilities instead
of assuming a specific database platform.

### Version awareness

Queries should consider MySQL version compatibility.

Where possible:

- use stable metadata sources
- avoid unsupported internal tables
- document minimum supported versions
- isolate version-specific queries

## Supported Metadata Sources

Preferred sources:

- `performance_schema`
- `information_schema`
- `sys` schema
- `SHOW` commands where appropriate

Internal InnoDB tables should only be used when required and should be clearly
documented.

## File Naming Convention

SQL files should use descriptive names:
```
<action>_<object>.sql
```

Examples:
- `get_version.sql`
- `get_variables.sql`
- `get_status.sql`
- `list_engines.sql`
- `detect_features.sql`



## Query Requirements

Each SQL file should:

- contain only SQL
- avoid UI-specific formatting
- use parameters when required
- return predictable column names
- include comments for complex logic

Example:

```sql
-- Retrieve server version information

SELECT
    @@version AS version,
    @@version_comment AS version_comment;
```

## Usage

Server SQL files are executed through the service layer using the database
connector abstraction.

The UI layer should not execute SQL directly.

Flow:
```
UI
 |
 v
Server Service
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

- MySQL version-specific SQL folders
- Aurora detection queries
- Percona feature detection
- replication topology detection
- backup capability detection
- security configuration checks
