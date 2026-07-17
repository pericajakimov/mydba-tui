# Monitoring

## Purpose

The Monitoring module provides a lightweight, real-time overview of the operational state of the connected MySQL server.

Its purpose is **situational awareness**, not deep performance analysis.

`mydba` is not intended to replace monitoring systems such as PMM, Grafana, CloudWatch, or similar tools. Instead, it should allow a DBA connected over SSH to quickly answer the question:

> "Is this server currently under load, and what is happening right now?"

---

# Design Goals

The Monitoring module should:

- Load quickly.
- Consume minimal server resources.
- Require no additional configuration.
- Present only the most useful operational metrics.
- Be readable in a terminal.
- Avoid overwhelming the user.

---

# Philosophy

Monitoring is intentionally kept simple.

When detailed performance analysis is required, dedicated monitoring platforms should be used.

The Monitoring page exists to provide a quick operational snapshot while working interactively on the server.

---

# Refresh Model

Monitoring updates automatically at a configurable refresh interval.

The default interval should balance responsiveness with minimal overhead.

Typical refresh interval:

- 2–5 seconds

The refresh mechanism should execute lightweight queries only.

---

# Screen Layout

The Monitoring screen contains two sections:

1. Live graphs
2. Instant metrics

Example layout:

```
+--------------------------------------------------------------+

 Connections                Queries / sec

 ████▇▆▆▅▅                 ▂▃▄▅▆▇██

---------------------------------------------------------------

 InnoDB Reads              InnoDB Writes

 ▂▂▃▄▅▅▆█                 ▁▂▂▃▄▅▇█

---------------------------------------------------------------

Replication Lag:      0 sec
Current Connections:  154 / 2000
Server Uptime:        12d 04h
Threads Running:      8

+--------------------------------------------------------------+
```

The exact layout may evolve, but the module should remain compact and easy to scan.

---

# Live Graphs

The initial implementation includes four graphs.

## Current Connections

Shows the number of active client connections over time.

This helps identify sudden connection spikes.

---

## Queries per Second

Displays the current query execution rate.

The value is calculated from global status counters.

This provides an immediate indication of server activity.

---

## InnoDB Reads

Displays the rate of physical and/or logical InnoDB read operations.

The exact implementation may evolve based on the most useful available metrics.

---

## InnoDB Writes

Displays the rate of InnoDB write operations.

This provides a quick indication of write activity on the server.

---

# Instant Metrics

Some information is better represented as numbers rather than graphs.

The initial implementation includes:

- Current connections
- Maximum configured connections
- Threads running
- Server uptime

Additional metrics may be introduced later.

---

# Replication

If the connected server is a replica, display:

- Current replication lag

If the connected server is a primary, replication lag is not displayed.

Future versions may also display replica health summaries when supported by the backend.

---

# Server Awareness

The Monitoring module adapts to the connected server.

Examples include:

- Oracle MySQL
- AWS Aurora
- Percona Server
- Percona XtraDB Cluster

Only metrics that can be reliably collected on the detected platform should be displayed.

---

# Performance Impact

Monitoring queries must be lightweight.

The module should avoid:

- Expensive table scans
- Large metadata queries
- Frequent complex joins

The Monitoring page must never become a noticeable source of database load.

---

# Pause and Resume

Automatic refresh should pause when:

- The Monitoring page is not active.
- The application loses the current connection.

Refreshing resumes automatically when the Monitoring page becomes active again.

---

# Historical Data

The Monitoring module displays only data collected during the current application session.

It is **not** a historical monitoring system.

Long-term metrics remain the responsibility of dedicated monitoring platforms.

---

# SQL Transparency

All SQL executed by the Monitoring module is written to the SQL log.

This allows DBAs to understand exactly how each metric is calculated and optimize or replace queries in future versions if needed.

---

# Future Enhancements

Possible future additions include:

- Buffer Pool activity
- Redo log throughput
- Temporary table creation rate
- Network traffic
- Replica topology overview
- Group Replication status
- Galera / PXC cluster status
- Aurora-specific replica information
- Custom user-defined monitoring widgets

These features are intentionally deferred to keep the initial implementation focused and lightweight.

---

# Design Principles

The Monitoring module follows these principles:

- Lightweight by default.
- Operational awareness over deep analytics.
- Minimal impact on the database.
- Automatic refresh only while active.
- Clear visual presentation.
- SQL transparency.
- Extensible architecture.
