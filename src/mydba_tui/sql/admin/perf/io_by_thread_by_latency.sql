-- Global I/O by thread (latency), from the sys schema.
-- Called from: services/performance.py -> fetch_view() (I/O detail; global)
-- Server-global context (not filtered to a single file): which threads drive
-- I/O latency. Sorted by descending total latency by default.
SELECT
    user,
    total,
    total_latency,
    min_latency,
    avg_latency,
    max_latency,
    thread_id,
    processlist_id
FROM
    sys.io_by_thread_by_latency
