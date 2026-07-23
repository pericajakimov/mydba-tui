-- Partition details for a table.
-- Called from: services/browser.py → get_table_partitions()
-- Returns one row per partition with method, expression, description, and sizes.
-- Non-partitioned tables return a single row with partition_name = NULL.
SELECT
    partition_name,
    partition_method,
    partition_expression,
    partition_description,
    partition_ordinal_position,
    table_rows,
    data_length,
    index_length
FROM
    information_schema.partitions
WHERE
    table_schema = '{schema}'
    AND table_name = '{table}'
    AND partition_name IS NOT NULL
ORDER BY
    partition_ordinal_position
