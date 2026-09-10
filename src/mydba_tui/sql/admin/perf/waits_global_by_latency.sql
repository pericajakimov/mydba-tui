-- Global wait events by total latency, from the sys schema.
-- Called from: services/performance.py -> fetch_view() (Performance > Waits)
-- sys.waits_global_by_latency groups server wait events by event, sorted by
-- descending total latency (idle events excluded). The `events` column is the
-- event name and the drill-down key. Needs the wait/* performance_schema
-- instruments enabled to show data.
SELECT
    events,
    total,
    total_latency,
    avg_latency,
    max_latency
FROM
    sys.waits_global_by_latency
