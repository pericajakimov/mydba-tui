-- Outgoing foreign keys: constraints defined ON this table.
-- Called from: services/browser.py → get_table_fk_outgoing()
-- Returns one row per column per FK constraint.
-- Columns grouped by constraint_name + ordinal_position reconstruct multi-column FKs.
SELECT
    rc.constraint_name,
    kcu.column_name,
    kcu.referenced_table_name,
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
    AND rc.table_name = '{table}'
ORDER BY
    rc.constraint_name,
    kcu.ordinal_position
