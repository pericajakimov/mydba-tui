-- All triggers and their action statements, for dependency analysis.
-- Called from: services/dependencies.py → _enumerate_objects()
SELECT
    trigger_schema,
    trigger_name,
    action_statement
FROM
    information_schema.triggers
