SELECT
    (SELECT COUNT(*) FROM information_schema.tables
     WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE') AS tables_count,
    (SELECT COUNT(*) FROM information_schema.tables
     WHERE table_schema = '{schema}' AND table_type IN ('VIEW', 'SYSTEM VIEW')) AS views_count,
    (SELECT COUNT(*) FROM information_schema.routines
     WHERE routine_schema = '{schema}' AND routine_type = 'PROCEDURE') AS procedures_count,
    (SELECT COUNT(*) FROM information_schema.routines
     WHERE routine_schema = '{schema}' AND routine_type = 'FUNCTION') AS functions_count,
    (SELECT COUNT(*) FROM information_schema.events
     WHERE event_schema = '{schema}') AS events_count,
    (SELECT COUNT(*) FROM information_schema.triggers
     WHERE trigger_schema = '{schema}') AS triggers_count
