-- InnoDB buffer-pool footprint for one table, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Tables detail)
-- Keyed on schema + table ({table_schema}, {table_name} bound as parameters,
-- not inlined). Shows how much of the buffer pool the table occupies.
SELECT
    innodb_buffer_allocated,
    innodb_buffer_data,
    innodb_buffer_free,
    innodb_buffer_pages,
    innodb_buffer_pages_hashed,
    innodb_buffer_pages_old,
    innodb_buffer_rows_cached
FROM
    sys.schema_table_statistics_with_buffer
WHERE
    table_schema = %s
    AND table_name = %s
