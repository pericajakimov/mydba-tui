-- Per-user breakdown for one wait event, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Waits detail)
-- Keyed on the event name ({event} bound as a parameter, not inlined).
SELECT
    user,
    total,
    total_latency,
    avg_latency,
    max_latency
FROM
    sys.waits_by_user_by_latency
WHERE
    event = %s
ORDER BY
    total_latency DESC
