-- Per-stage breakdown for one host, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Hosts detail)
-- {host} is bound as a parameter, not inlined. Ordered by descending latency.
SELECT
    event_name,
    total,
    total_latency,
    avg_latency
FROM
    sys.host_summary_by_stages
WHERE
    host = %s
ORDER BY
    total_latency DESC
