-- Per-statement-type breakdown for one host, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Hosts detail)
-- {host} is bound as a parameter, not inlined. Ordered by descending latency.
SELECT
    statement,
    total,
    total_latency,
    max_latency,
    lock_latency,
    rows_sent,
    rows_examined,
    rows_affected,
    full_scans
FROM
    sys.host_summary_by_statement_type
WHERE
    host = %s
ORDER BY
    total_latency DESC
