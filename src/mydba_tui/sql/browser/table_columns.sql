-- Column details for the table metadata view.
-- Called from: services/browser.py → get_table_columns()
-- Returns all columns with type, nullability, keys, defaults, and extras.
SELECT
    ordinal_position,
    column_name,
    column_type,
    is_nullable,
    column_key,
    column_default,
    extra,
    column_comment
FROM
    information_schema.columns
WHERE
    table_schema = '{schema}'
    AND table_name = '{table}'
ORDER BY
    ordinal_position
