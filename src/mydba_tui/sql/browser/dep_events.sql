-- All events and their definitions, for dependency analysis.
-- Called from: services/dependencies.py → _enumerate_objects()
SELECT
    event_schema,
    event_name,
    event_definition
FROM
    information_schema.events
