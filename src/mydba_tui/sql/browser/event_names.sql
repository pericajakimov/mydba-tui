-- Event names for listing under a schema in the Object Browser.
-- Called from: services/browser.py → get_objects(category="events")
SELECT
    event_name
FROM
    information_schema.events
WHERE
    event_schema = '{schema}'
ORDER BY
    event_name
