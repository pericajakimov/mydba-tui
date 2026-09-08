-- All schema names, for SQL editor autocomplete.
-- Called from: ui/screens/workspace.py autocomplete cache
SELECT
    schema_name
FROM
    information_schema.schemata
