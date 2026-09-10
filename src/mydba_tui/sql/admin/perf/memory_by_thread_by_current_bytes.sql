-- Current memory use grouped by thread, from the sys schema.
-- Called from: services/performance.py -> fetch_view() (Memory detail; global)
-- Server-global context: which threads hold currently-allocated memory. Sorted
-- by descending current allocation by default.
SELECT
    thread_id,
    user,
    current_count_used,
    current_allocated,
    current_avg_alloc,
    current_max_alloc,
    total_allocated
FROM
    sys.memory_by_thread_by_current_bytes
