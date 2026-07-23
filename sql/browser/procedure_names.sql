-- Stored procedure names for listing under a schema in the Object Browser.
-- Called from: services/browser.py → get_objects(category="procedures")
SELECT
    routine_name
FROM
    information_schema.routines
WHERE
    routine_schema = '{schema}'
    AND routine_type = 'PROCEDURE'
ORDER BY
    routine_name
