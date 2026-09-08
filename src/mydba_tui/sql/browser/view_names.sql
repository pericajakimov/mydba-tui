-- View names for listing under a schema in the Object Browser.
-- Called from: services/browser.py → get_objects(category="views")
-- Includes SYSTEM VIEW for information_schema/performance_schema.
SELECT
    table_name
FROM
    information_schema.tables
WHERE
    table_schema = '{schema}'
    AND table_type IN ('VIEW', 'SYSTEM VIEW')
ORDER BY
    table_name
