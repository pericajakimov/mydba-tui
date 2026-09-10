-- Per-user activity summary, from the sys schema.
-- Called from: services/performance.py -> fetch_view() (Performance > Users)
-- sys.user_summary aggregates statement activity, file I/O, connections, and
-- memory per client user. Sorted by descending total latency by default, so
-- the busiest users are on top. `user` is the drill-down key.
SELECT
    user,
    statements,
    statement_latency,
    statement_avg_latency,
    table_scans,
    file_ios,
    file_io_latency,
    current_connections,
    total_connections,
    unique_hosts,
    current_memory,
    total_memory_allocated
FROM
    sys.user_summary
