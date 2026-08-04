-- General information for a trigger.
-- Called from: services/browser.py → get_trigger_info()
SELECT
    trigger_schema,
    trigger_name,
    event_manipulation,
    event_object_schema,
    event_object_table,
    action_timing,
    action_statement,
    action_order,
    definer,
    created
FROM
    information_schema.triggers
WHERE
    trigger_schema = '{schema}'
    AND trigger_name = '{name}'
