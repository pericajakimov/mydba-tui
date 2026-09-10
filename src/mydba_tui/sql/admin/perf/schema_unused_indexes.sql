-- Unused indexes, from the sys schema.
-- Called from: services/performance.py -> fetch_view() (Performance > Indexes)
-- sys.schema_unused_indexes lists indexes with no recorded events — candidates
-- for removal (they cost writes and space with no read benefit). Only
-- meaningful once the server has run a representative workload.
SELECT
    object_schema,
    object_name,
    index_name
FROM
    sys.schema_unused_indexes
