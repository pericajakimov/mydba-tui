-- Active sessions from performance_schema (MySQL 8.0+, Percona, PXC, Aurora v3).
-- Called from: services/processlist.py → fetch_processes()
-- The client program name is joined from session_connect_attrs, as Workbench does.
SELECT
    p.ID AS Id,
    p.USER AS User,
    p.HOST AS Host,
    p.DB AS db,
    p.COMMAND AS Command,
    p.TIME AS Time,
    p.STATE AS State,
    p.INFO AS Info,
    a.ATTR_VALUE AS Program
FROM
    performance_schema.processlist p
    LEFT JOIN performance_schema.session_connect_attrs a
        ON a.PROCESSLIST_ID = p.ID
        AND a.ATTR_NAME = 'program_name'
ORDER BY
    p.TIME DESC
