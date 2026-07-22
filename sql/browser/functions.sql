SELECT
    routine_name
FROM
    information_schema.routines
WHERE
    routine_schema = '{schema}'
    AND routine_type = 'FUNCTION'
ORDER BY
    routine_name
