-- Incoming foreign keys: constraints from OTHER tables referencing this table.
-- Called from: services/browser.py → get_table_fk_incoming()
-- Returns one row per column per FK constraint.
SELECT
    rc.constraint_name,
    rc.table_name AS source_table,
    kcu.column_name AS source_column,
    kcu.referenced_column_name,
    kcu.ordinal_position,
    rc.delete_rule,
    rc.update_rule
FROM
    information_schema.referential_constraints rc
    JOIN information_schema.key_column_usage kcu
        ON kcu.constraint_schema = rc.constraint_schema
        AND kcu.constraint_name = rc.constraint_name
        AND kcu.table_schema = rc.constraint_schema
        AND kcu.table_name = rc.table_name
WHERE
    rc.constraint_schema = '{schema}'
    AND rc.referenced_table_name = '{table}'
ORDER BY
    rc.table_name,
    rc.constraint_name,
    kcu.ordinal_position
