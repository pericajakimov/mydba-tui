SELECT
    table_name
FROM
    information_schema.tables
WHERE
    table_schema = '{schema}'
    AND table_type IN ('VIEW', 'SYSTEM VIEW')
ORDER BY
    table_name
