-- Index details for the table metadata view.
-- Called from: services/browser.py → get_table_indexes()
-- Returns one row per column per index with cardinality and visibility.
-- Requires MySQL 8.0+ for is_visible and expression columns.
SELECT
    index_name,
    non_unique,
    seq_in_index,
    column_name,
    cardinality,
    nullable,
    index_type,
    is_visible,
    expression,
    index_comment
FROM
    information_schema.statistics
WHERE
    table_schema = '{schema}'
    AND table_name = '{table}'
ORDER BY
    index_name,
    seq_in_index
