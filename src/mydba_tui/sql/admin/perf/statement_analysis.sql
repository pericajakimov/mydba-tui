-- Top queries by total latency, from the sys schema statement digest view.
-- Called from: services/performance.py -> fetch_statement_analysis()
-- sys.statement_analysis is a friendly view over
-- performance_schema.events_statements_summary_by_digest. The pretty (non-x$)
-- view already formats latency/bytes as human strings and is sorted by
-- descending total latency by default, so the top rows are the heaviest
-- statements. digest is the stable key used to fetch the full sample text on
-- demand.
SELECT
    query,
    db,
    exec_count,
    total_latency,
    avg_latency,
    max_latency,
    lock_latency,
    rows_sent_avg,
    rows_examined_avg,
    tmp_tables,
    tmp_disk_tables,
    full_scan,
    digest
FROM
    sys.statement_analysis
LIMIT 200
