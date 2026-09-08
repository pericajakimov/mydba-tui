-- Triggers defined on a specific table.
-- Called from: services/browser.py → get_table_triggers()
-- Returns one row per trigger with timing, event, definer, created, and body.
SELECT
    trigger_name,
    event_manipulation,
    action_timing,
    definer,
    created,
    action_statement
FROM
    information_schema.triggers
WHERE
    event_object_schema = '{schema}'
    AND event_object_table = '{table}'
ORDER BY
    action_order
