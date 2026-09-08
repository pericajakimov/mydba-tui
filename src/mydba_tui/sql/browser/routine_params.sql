-- Parameters for a stored procedure or function.
-- Called from: services/browser.py → get_routine_params()
SELECT
    ordinal_position,
    parameter_mode,
    parameter_name,
    dtd_identifier
FROM
    information_schema.parameters
WHERE
    specific_schema = '{schema}'
    AND specific_name = '{name}'
    AND routine_type = '{routine_type}'
ORDER BY
    ordinal_position
