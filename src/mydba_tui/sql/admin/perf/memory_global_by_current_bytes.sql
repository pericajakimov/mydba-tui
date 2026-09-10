-- Current memory use by allocation type, from the sys schema.
-- Called from: services/performance.py -> fetch_view() (Performance > Memory)
-- sys.memory_global_by_current_bytes groups currently-allocated memory by event
-- (allocation type), sorted by descending current allocation. Requires the
-- memory/* performance_schema instruments to be enabled to show data.
SELECT
    event_name,
    current_count,
    current_alloc,
    current_avg_alloc,
    high_count,
    high_alloc
FROM
    sys.memory_global_by_current_bytes
