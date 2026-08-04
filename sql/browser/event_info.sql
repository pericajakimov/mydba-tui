-- General information for a scheduled event.
-- Called from: services/browser.py → get_event_info()
SELECT
    event_schema,
    event_name,
    definer,
    event_type,
    execute_at,
    interval_value,
    interval_field,
    starts,
    ends,
    status,
    on_completion,
    created,
    last_altered,
    event_definition,
    event_comment
FROM
    information_schema.events
WHERE
    event_schema = '{schema}'
    AND event_name = '{name}'
