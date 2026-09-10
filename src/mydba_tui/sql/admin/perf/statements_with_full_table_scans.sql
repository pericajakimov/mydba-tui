-- Statements doing full table scans, from the sys schema.
-- Called from: services/performance.py -> fetch_view() (Performance > Full Scans)
-- sys.statements_with_full_table_scans lists normalized statements that scanned
-- without an index, sorted by descending no-index percentage then latency.
-- digest is the drill-down key (full text + sample, open in Workspace).
SELECT
    query,
    db,
    exec_count,
    total_latency,
    no_index_used_count,
    no_index_used_pct,
    rows_examined,
    rows_examined_avg,
    digest
FROM
    sys.statements_with_full_table_scans
LIMIT 200
