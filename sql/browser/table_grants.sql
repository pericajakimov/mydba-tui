-- Effective privileges on a table combining global, schema, and table-level grants.
-- Called from: services/browser.py → get_table_grants()
-- Returns one row per user/host/level with their privileges.
-- Requires SELECT on mysql.user, mysql.db, mysql.tables_priv.
SELECT
    user,
    host,
    'GLOBAL' AS grant_level,
    CONCAT_WS(',',
        IF(Select_priv = 'Y', 'SELECT', NULL),
        IF(Insert_priv = 'Y', 'INSERT', NULL),
        IF(Update_priv = 'Y', 'UPDATE', NULL),
        IF(Delete_priv = 'Y', 'DELETE', NULL),
        IF(Create_priv = 'Y', 'CREATE', NULL),
        IF(Drop_priv = 'Y', 'DROP', NULL),
        IF(Grant_priv = 'Y', 'GRANT', NULL),
        IF(References_priv = 'Y', 'REFERENCES', NULL),
        IF(Index_priv = 'Y', 'INDEX', NULL),
        IF(Alter_priv = 'Y', 'ALTER', NULL),
        IF(Trigger_priv = 'Y', 'TRIGGER', NULL)
    ) AS privileges
FROM
    mysql.user
WHERE
    (Select_priv = 'Y' OR Insert_priv = 'Y' OR Update_priv = 'Y'
     OR Delete_priv = 'Y' OR Create_priv = 'Y' OR Drop_priv = 'Y'
     OR Grant_priv = 'Y' OR References_priv = 'Y' OR Index_priv = 'Y'
     OR Alter_priv = 'Y' OR Trigger_priv = 'Y')
    AND user != ''

UNION ALL

SELECT
    user,
    host,
    'SCHEMA' AS grant_level,
    CONCAT_WS(',',
        IF(Select_priv = 'Y', 'SELECT', NULL),
        IF(Insert_priv = 'Y', 'INSERT', NULL),
        IF(Update_priv = 'Y', 'UPDATE', NULL),
        IF(Delete_priv = 'Y', 'DELETE', NULL),
        IF(Create_priv = 'Y', 'CREATE', NULL),
        IF(Drop_priv = 'Y', 'DROP', NULL),
        IF(Grant_priv = 'Y', 'GRANT', NULL),
        IF(References_priv = 'Y', 'REFERENCES', NULL),
        IF(Index_priv = 'Y', 'INDEX', NULL),
        IF(Alter_priv = 'Y', 'ALTER', NULL),
        IF(Trigger_priv = 'Y', 'TRIGGER', NULL)
    ) AS privileges
FROM
    mysql.db
WHERE
    db = '{schema}'
    AND user != ''

UNION ALL

SELECT
    user,
    host,
    'TABLE' AS grant_level,
    TRIM(BOTH ',' FROM
        REPLACE(REPLACE(REPLACE(REPLACE(table_priv,
            'Create View', ''),
            'Show view', ''),
            ',,', ','),
            ',,', ',')
    ) AS privileges
FROM
    mysql.tables_priv
WHERE
    db = '{schema}'
    AND table_name = '{table}'
    AND user != ''
    AND table_priv != ''

UNION ALL

SELECT
    user,
    host,
    'COLUMN' AS grant_level,
    CONCAT(column_priv, ' (', column_name, ')') AS privileges
FROM
    mysql.columns_priv
WHERE
    db = '{schema}'
    AND table_name = '{table}'
    AND user != ''

ORDER BY
    user,
    host,
    FIELD(grant_level, 'GLOBAL', 'SCHEMA', 'TABLE', 'COLUMN')
