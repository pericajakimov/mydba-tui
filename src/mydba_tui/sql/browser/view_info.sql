-- General information for a view.
-- Called from: services/browser.py → get_view_info()
SELECT
    table_schema,
    table_name,
    view_definition,
    check_option,
    is_updatable,
    definer,
    security_type,
    character_set_client,
    collation_connection
FROM
    information_schema.views
WHERE
    table_schema = '{schema}'
    AND table_name = '{view}'
