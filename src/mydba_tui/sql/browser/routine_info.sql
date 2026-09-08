-- General information for a stored procedure or function.
-- Called from: services/browser.py → get_routine_info()
SELECT
    routine_schema,
    routine_name,
    routine_type,
    dtd_identifier,
    routine_definition,
    is_deterministic,
    sql_data_access,
    security_type,
    definer,
    created,
    last_altered,
    routine_comment
FROM
    information_schema.routines
WHERE
    routine_schema = '{schema}'
    AND routine_name = '{name}'
    AND routine_type = '{routine_type}'
