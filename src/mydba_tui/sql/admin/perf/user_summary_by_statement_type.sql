-- Per-statement-type breakdown for one user, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Users detail)
-- {user} is bound as a parameter, not inlined. Ordered by descending latency.
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
    sys.user_summary_by_statement_type
WHERE
    user = %s
ORDER BY
    total_latency DESC
