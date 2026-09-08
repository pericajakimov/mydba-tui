-- Table names for listing under a schema in the Object Browser.
-- Called from: services/browser.py → get_objects(category="tables")
SELECT
    table_name
FROM
    information_schema.tables
WHERE
    table_schema = '{schema}'
    AND table_type = 'BASE TABLE'
ORDER BY
    table_name
