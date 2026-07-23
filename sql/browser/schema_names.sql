-- Schema names for the Object Browser tree.
-- Called from: services/browser.py → get_schemas()
-- Returns all schema (database) names on the server.
SELECT
    schema_name
FROM
    information_schema.schemata
ORDER BY
    schema_name
