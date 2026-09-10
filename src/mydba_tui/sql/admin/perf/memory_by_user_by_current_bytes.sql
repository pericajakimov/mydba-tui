-- Current memory use grouped by user, from the sys schema.
-- Called from: services/performance.py -> fetch_view() (Memory detail; global)
-- Server-global context: which users hold currently-allocated memory. Sorted
-- by descending current allocation by default.
SELECT
    user,
    current_count_used,
    current_allocated,
    current_avg_alloc,
    current_max_alloc,
    total_allocated
FROM
    sys.memory_by_user_by_current_bytes
