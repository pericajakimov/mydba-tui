-- Index access statistics for one table, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Tables detail)
-- Keyed on schema + table ({table_schema}, {table_name} bound as parameters,
-- not inlined). Ordered by descending select latency (hottest index first).
SELECT
    index_name,
    rows_selected,
    select_latency,
    rows_inserted,
    insert_latency,
    rows_updated,
    update_latency,
    rows_deleted,
    delete_latency
FROM
    sys.schema_index_statistics
WHERE
    table_schema = %s
    AND table_name = %s
ORDER BY
    select_latency DESC
