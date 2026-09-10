-- Statement latency breakdown for one host, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Hosts detail)
-- {host} is bound as a parameter, not inlined.
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
    sys.host_summary_by_statement_latency
WHERE
    host = %s
