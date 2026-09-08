-- Trigger names for listing under a schema in the Object Browser.
-- Called from: services/browser.py → get_objects(category="triggers")
SELECT
    trigger_name
FROM
    information_schema.triggers
WHERE
    trigger_schema = '{schema}'
ORDER BY
    trigger_name
