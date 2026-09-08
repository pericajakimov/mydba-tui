-- Recent statements for a connection, from performance_schema.
-- Called from: services/transactions.py → fetch_statement_history()
-- {conn_id} is the PROCESSLIST_ID (an integer). TIMER_WAIT is picoseconds;
-- converted to milliseconds. Ordered most recent first.
SELECT
    h.SQL_TEXT AS sql_text,
    h.TIMER_WAIT / 1000000000 AS duration_ms,
    h.EVENT_ID AS event_id
FROM
    performance_schema.events_statements_history h
    JOIN performance_schema.threads t
        ON t.THREAD_ID = h.THREAD_ID
WHERE
    t.PROCESSLIST_ID = {conn_id}
    AND h.SQL_TEXT IS NOT NULL
ORDER BY
    h.EVENT_ID DESC
LIMIT 20
