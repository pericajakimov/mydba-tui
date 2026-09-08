-- Procedures and functions in a schema, for SQL editor autocomplete.
-- Called from: ui/screens/workspace.py autocomplete cache
-- {schema} is substituted with a single-quote-escaped schema name.
SELECT
    routine_name,
    routine_type
FROM
    information_schema.routines
WHERE
    routine_schema = '{schema}'
