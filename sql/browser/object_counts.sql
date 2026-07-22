SELECT
    t.tables_count,
    t.views_count,
    r.procedures_count,
    r.functions_count,
    (SELECT COUNT(*) FROM information_schema.events
     WHERE event_schema = '{schema}') AS events_count,
    (SELECT COUNT(*) FROM information_schema.triggers
     WHERE trigger_schema = '{schema}') AS triggers_count
FROM
    (SELECT
        SUM(table_type = 'BASE TABLE') AS tables_count,
        SUM(table_type IN ('VIEW', 'SYSTEM VIEW')) AS views_count
     FROM information_schema.tables
     WHERE table_schema = '{schema}') t,
    (SELECT
        SUM(routine_type = 'PROCEDURE') AS procedures_count,
        SUM(routine_type = 'FUNCTION') AS functions_count
     FROM information_schema.routines
     WHERE routine_schema = '{schema}') r
