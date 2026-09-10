-- Per-file-I/O-event-type breakdown for one host, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Hosts detail)
-- {host} is bound as a parameter, not inlined. Ordered by descending latency.
SELECT
    event_name,
    total,
    total_latency,
    max_latency
FROM
    sys.host_summary_by_file_io_type
WHERE
    host = %s
ORDER BY
    total_latency DESC
