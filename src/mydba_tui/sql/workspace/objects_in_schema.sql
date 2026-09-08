-- Tables, views, and routines in a schema, for after-dot autocomplete.
-- Called from: ui/screens/workspace.py → _get_schema_objects_for()
-- {schema} is substituted with a single-quote-escaped schema name.
SELECT
    table_name
FROM
    information_schema.tables
WHERE
    table_schema = '{schema}'
UNION
SELECT
    routine_name
FROM
    information_schema.routines
WHERE
    routine_schema = '{schema}'
