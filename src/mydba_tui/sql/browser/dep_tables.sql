-- All base tables (dependency targets — no SQL definition to parse).
-- Called from: services/dependencies.py → _enumerate_tables()
SELECT
    table_schema,
    table_name
FROM
    information_schema.tables
WHERE
    table_type = 'BASE TABLE'
