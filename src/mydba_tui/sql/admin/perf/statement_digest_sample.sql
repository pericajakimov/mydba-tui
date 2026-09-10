-- Full normalized text and a real sample for a statement digest.
-- Called from: services/performance.py -> fetch_statement_digest_sample()
-- Keyed by DIGEST. DIGEST_TEXT is the full normalized statement (the sys view
-- truncates query); QUERY_SAMPLE_TEXT is a concrete example seen by the server
-- (MySQL 8.0+, may be NULL). {digest} is bound as a parameter, not inlined.
SELECT
    DIGEST_TEXT AS digest_text,
    QUERY_SAMPLE_TEXT AS sample_text,
    SCHEMA_NAME AS schema_name,
    COUNT_STAR AS exec_count,
    FIRST_SEEN AS first_seen,
    LAST_SEEN AS last_seen
FROM
    performance_schema.events_statements_summary_by_digest
WHERE
    DIGEST = %s
LIMIT 1
