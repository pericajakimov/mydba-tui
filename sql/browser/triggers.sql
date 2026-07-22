SELECT
    trigger_name
FROM
    information_schema.triggers
WHERE
    trigger_schema = '{schema}'
ORDER BY
    trigger_name
