-- Foreign-key relationships between tables, for dependency analysis.
-- Called from: services/dependencies.py → _enumerate_foreign_keys()
-- Returns: source schema, source table, target schema, target table, constraint.
SELECT
    constraint_schema,
    table_name,
    constraint_schema,
    referenced_table_name,
    constraint_name
FROM
    information_schema.referential_constraints
