-- List all schemas (databases) on the server.
SELECT
    schema_name
FROM
    information_schema.schemata
ORDER BY
    schema_name
