SELECT
    event_name
FROM
    information_schema.events
WHERE
    event_schema = '{schema}'
ORDER BY
    event_name
