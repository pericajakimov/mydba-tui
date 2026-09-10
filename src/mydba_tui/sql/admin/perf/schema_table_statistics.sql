-- Per-table access statistics, from the sys schema.
-- Called from: services/performance.py -> fetch_view() (Performance > Tables)
-- sys.schema_table_statistics ranks tables by contention (total wait time),
-- with row read/insert/update/delete counts and I/O. table_schema + table_name
-- are the drill-down keys.
SELECT
    table_schema,
    table_name,
    total_latency,
    rows_fetched,
    fetch_latency,
    rows_inserted,
    rows_updated,
    rows_deleted,
    io_read,
    io_write
FROM
    sys.schema_table_statistics
