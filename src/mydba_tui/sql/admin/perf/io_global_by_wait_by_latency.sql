-- Global I/O by wait type (latency), from the sys schema.
-- Called from: services/performance.py -> fetch_view() (I/O detail; global)
-- Server-global context (not filtered to a single file): where I/O latency is
-- spent by event type. Sorted by descending total latency by default.
SELECT
    event_name,
    total,
    total_latency,
    avg_latency,
    max_latency,
    read_latency,
    write_latency,
    misc_latency,
    count_read,
    total_read,
    count_write,
    total_written
FROM
    sys.io_global_by_wait_by_latency
