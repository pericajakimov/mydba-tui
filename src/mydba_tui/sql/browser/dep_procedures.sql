-- All stored procedures and their bodies, for dependency analysis.
-- Called from: services/dependencies.py → _enumerate_objects()
SELECT
    routine_schema,
    routine_name,
    routine_definition
FROM
    information_schema.routines
WHERE
    routine_type = 'PROCEDURE'
