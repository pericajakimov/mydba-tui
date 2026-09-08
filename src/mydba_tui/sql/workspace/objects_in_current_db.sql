-- Tables and views in a schema, for SQL editor autocomplete.
-- Called from: ui/screens/workspace.py autocomplete cache
-- {schema} is substituted with a single-quote-escaped schema name.
SELECT
    table_name,
    table_type
FROM
    information_schema.tables
WHERE
    table_schema = '{schema}'
