-- InnoDB row-lock waits: which session is blocked, and which one blocks it.
-- Called from: services/locks.py -> fetch_lock_waits()
-- sys.innodb_lock_waits has pids but no user/host; join the process list twice
-- (waiting + blocking) to enrich. Ordered longest-waiting first.
SELECT
    w.wait_age_secs AS wait_age_secs,
    w.locked_table_schema AS locked_schema,
    w.locked_table_name AS locked_table,
    w.locked_type AS locked_type,
    w.waiting_pid AS waiting_pid,
    wp.USER AS waiting_user,
    wp.HOST AS waiting_host,
    w.waiting_lock_mode AS waiting_lock_mode,
    w.waiting_query AS waiting_query,
    w.blocking_pid AS blocking_pid,
    bp.USER AS blocking_user,
    bp.HOST AS blocking_host,
    w.blocking_lock_mode AS blocking_lock_mode,
    w.blocking_query AS blocking_query
FROM
    sys.innodb_lock_waits w
    LEFT JOIN information_schema.processlist wp
        ON wp.ID = w.waiting_pid
    LEFT JOIN information_schema.processlist bp
        ON bp.ID = w.blocking_pid
ORDER BY
    w.wait_age_secs DESC
