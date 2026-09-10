-- Per-stage breakdown for one user, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Users detail)
-- {user} is bound as a parameter, not inlined. Ordered by descending latency.
SELECT
    event_name,
    total,
    total_latency,
    avg_latency
FROM
    sys.user_summary_by_stages
WHERE
    user = %s
ORDER BY
    total_latency DESC
