-- Redundant (duplicate/dominated) indexes, from the sys schema.
-- Called from: services/performance.py -> fetch_view() (Indexes detail; global)
-- Server-global context: indexes made redundant by a dominant index, including
-- the ready-to-run DROP INDEX statement to remove each one.
SELECT
    table_schema,
    table_name,
    redundant_index_name,
    redundant_index_columns,
    dominant_index_name,
    dominant_index_columns,
    sql_drop_index
FROM
    sys.schema_redundant_indexes
