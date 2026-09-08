# SQL Monitoring Queries

This directory contains SQL statements used by the monitoring component of
mydba-tui.

The queries in this directory provide operational visibility into MySQL server
activity, performance, and health.

## Purpose

SQL files here retrieve monitoring information such as:

- active sessions
- running queries
- locks and waits
- transactions
- InnoDB status
- replication status
- performance statistics
- resource utilization
- database activity metrics

## Design Principles

### Operational visibility

Monitoring queries should provide information useful for daily DBA operations:

- identify active workloads
- troubleshoot performance issues
- investigate blocking sessions
- validate replication health
- inspect database state

### Read-only by design

Monitoring queries should not modify database state.

Expected query types:

- `SELECT`
- `SHOW`
- metadata inspection commands

No DDL or DML statements should exist in this directory.

## Preferred Data Sources

Monitoring queries should use:

- `performance_schema`
- `sys` schema
- `information_schema`
- `SHOW` commands
- InnoDB diagnostic interfaces when required

Preferred order:

1. `sys` schema for human-readable information
2. `performance_schema` for detailed metrics
3. `information_schema` for metadata
4. internal diagnostics when no alternative exists

## File Naming Convention

SQL files should use descriptive names:
```
<action>_<metric_or_object>.sql
```

Examples:
- `list_processes.sql`
- `active_transactions.sql`
- `blocking_locks.sql`
- `replication_status.sql`
- `innodb_status.sql`
- `buffer_pool_usage.sql`


## Query Requirements

Each SQL file should:

- contain only SQL
- be safe for production execution
- avoid modifying server state
- return predictable column names
- include comments explaining complex logic
- document required privileges

Example:

```sql
-- Show currently running sessions

SELECT
    *
FROM
    information_schema.processlist
ORDER BY
    time DESC;
```

## Performance Considerations

Monitoring queries may run frequently.

Queries should:

- avoid expensive full scans
- use appropriate filters
- limit returned rows where possible
- avoid impacting production workloads

For high-frequency monitoring:

- prefer lightweight queries
- cache expensive calculations
- execute at controlled intervals


## Query Categories

Future SQL files may be organized into:
```
monitoring/
├── sessions/
├── locks/
├── transactions/
├── replication/
├── innodb/
├── performance/
└── resources/
```

## Server Compatibility

Monitoring capabilities depend on the detected server type.

Examples:

- MySQL Community Server
- Percona Server
- AWS Aurora MySQL

Vendor-specific monitoring queries should be isolated and clearly named.

## Future Extensions

This directory may later include:

- real-time dashboards
- performance snapshots
- historical metric collection
- deadlock analysis
- replication lag analysis
- slow query investigation helpers
- Performance Schema report queries
