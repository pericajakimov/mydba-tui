-- Active sessions from information_schema (MariaDB, older MySQL).
-- Called from: services/processlist.py → fetch_processes()
-- No program-name source here; Program is NULL to keep a consistent shape.
SELECT
    ID AS Id,
    USER AS User,
    HOST AS Host,
    DB AS db,
    COMMAND AS Command,
    TIME AS Time,
    STATE AS State,
    INFO AS Info,
    NULL AS Program
FROM
    information_schema.PROCESSLIST
ORDER BY
    TIME DESC
