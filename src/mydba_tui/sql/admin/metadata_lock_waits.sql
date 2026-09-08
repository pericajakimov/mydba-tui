-- Table metadata-lock (MDL) waits: sessions blocked on a table lock and the
-- session blocking them (e.g. an ALTER waiting on an open transaction).
-- Called from: services/metadata_locks.py -> fetch_metadata_lock_waits()
-- Sourced from the sys schema view, which already carries account info.
SELECT DISTINCT
    w.waiting_query_secs AS wait_age_secs,
    w.object_schema AS object_schema,
    w.object_name AS object_name,
    w.waiting_pid AS waiting_pid,
    w.waiting_account AS waiting_account,
    w.waiting_lock_type AS waiting_lock_type,
    w.waiting_query AS waiting_query,
    w.blocking_pid AS blocking_pid,
    w.blocking_account AS blocking_account,
    w.blocking_lock_type AS blocking_lock_type
FROM
    sys.schema_table_lock_waits w
ORDER BY
    wait_age_secs DESC
