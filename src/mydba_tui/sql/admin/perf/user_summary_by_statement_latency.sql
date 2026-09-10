-- Statement latency breakdown for one user, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Users detail)
-- {user} is bound as a parameter, not inlined.
SELECT
    statements,
    statement_latency,
    statement_avg_latency,
    table_scans,
    rows_sent,
    rows_examined,
    rows_affected,
    full_scans
FROM
    sys.user_summary_by_statement_latency
WHERE
    user = %s
