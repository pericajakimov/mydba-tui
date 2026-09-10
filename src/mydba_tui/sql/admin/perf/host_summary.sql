-- Per-host activity summary, from the sys schema.
-- Called from: services/performance.py -> fetch_view() (Performance > Hosts)
-- sys.host_summary aggregates statement activity, file I/O, connections, and
-- memory per client host. `host` is the drill-down key.
SELECT
    host,
    statements,
    statement_latency,
    statement_avg_latency,
    table_scans,
    file_ios,
    file_io_latency,
    current_connections,
    total_connections,
    unique_users,
    current_memory,
    total_memory_allocated
FROM
    sys.host_summary
