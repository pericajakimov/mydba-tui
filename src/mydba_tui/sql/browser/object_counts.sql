-- Object counts per schema for the Object Browser tree.
-- Called from: services/browser.py → get_object_counts()
-- Returns counts of tables, views, procedures, functions, events, triggers.
-- Uses derived tables to scan information_schema efficiently:
--   tables + views in one pass, procedures + functions in one pass.
SELECT
    t.tables_count,
    t.views_count,
    r.procedures_count,
    r.functions_count,
    e.events_count,
    tr.triggers_count
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
     WHERE routine_schema = '{schema}') r,
    (SELECT
        COUNT(*) AS events_count
     FROM information_schema.events
     WHERE event_schema = '{schema}') e,
    (SELECT
        COUNT(*) AS triggers_count
     FROM information_schema.triggers
     WHERE trigger_schema = '{schema}') tr
