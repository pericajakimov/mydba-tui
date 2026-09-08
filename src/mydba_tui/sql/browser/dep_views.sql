-- All views and their definitions, for dependency analysis.
-- Called from: services/dependencies.py → _enumerate_objects()
SELECT
    table_schema,
    table_name,
    view_definition
FROM
    information_schema.views
