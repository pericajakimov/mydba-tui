-- MySQL accounts classified into logical groups for the Administration Users
-- tab. Called from: services/users.py -> fetch_users()
--
-- The grouping lives entirely in the CASE below so it can be tailored to a
-- team's conventions by editing this file — the application only renders the
-- result. Rules are evaluated top to bottom (first match wins):
--
--   System Users        — reserved server accounts (root, mysql.sys, etc.)
--   Admin Users         — global SUPER, or global CREATE + ALTER + DROP
--   Personal Users      — username contains a dot (e.g. name.surname)
--   Application Users   — CREATE + ALTER + DROP on at least one schema
--                         (GRANT ALL ON schema.*); checked before read-only so
--                         an app account with extra SELECT grants stays here
--   Monitoring Users    — global PROCESS (checked before Replication, since a
--                         monitoring account often also holds replication privs)
--   Replication Users   — global REPLICATION SLAVE or REPLICATION CLIENT
--   Read-Only Users     — global SELECT, or schema-level SELECT with no writes
--   Special Purpose Users — anything else
--
-- Colours: the inner query classifies each account into a group; the outer
-- query maps a group name to a colour. Edit the colour map to taste, or leave a
-- group's colour as '' to let the application auto-assign a distinct one.
-- Usable colour names:
--   red, green, yellow, blue, magenta, cyan, white, orange1, purple,
--   deep_pink2, spring_green2, gold1, turquoise2, dodger_blue1, hot_pink,
--   grey62  (any Rich/Textual colour name or #rrggbb hex also works).
SELECT
    g.group_name AS group_name,
    CASE g.group_name
        WHEN 'Admin Users' THEN 'red'
        WHEN 'System Users' THEN 'grey62'
        WHEN 'Read-Only Users' THEN 'green'
        WHEN 'Application Users' THEN 'dodger_blue1'
        WHEN 'Personal Users' THEN 'orange1'
        WHEN 'Monitoring Users' THEN 'cyan'
        WHEN 'Replication Users' THEN 'magenta'
        WHEN 'Special Purpose Users' THEN 'yellow'
        ELSE ''
    END AS group_color,
    g.user AS user,
    g.host AS host,
    g.account_locked AS account_locked,
    g.password_expired AS password_expired,
    g.password_last_changed AS password_last_changed,
    g.plugin AS plugin
FROM (
    -- Inner query: classify each account into a group (first match wins).
    -- Schema-level checks use correlated subqueries against mysql.db.
    SELECT
        CASE
            WHEN u.User IN ('root', 'mysql.sys', 'mysql.session', 'mysql.infoschema')
                THEN 'System Users'
            WHEN u.Super_priv = 'Y'
                OR (u.Create_priv = 'Y' AND u.Alter_priv = 'Y' AND u.Drop_priv = 'Y')
                THEN 'Admin Users'
            WHEN u.User LIKE '%.%'
                THEN 'Personal Users'
            WHEN EXISTS (
                    SELECT 1 FROM mysql.db d
                    WHERE d.User = u.User AND d.Host = u.Host
                        AND d.Create_priv = 'Y' AND d.Alter_priv = 'Y'
                        AND d.Drop_priv = 'Y'
                )
                THEN 'Application Users'
            WHEN u.Process_priv = 'Y'
                THEN 'Monitoring Users'
            WHEN u.Repl_slave_priv = 'Y' OR u.Repl_client_priv = 'Y'
                THEN 'Replication Users'
            WHEN u.Select_priv = 'Y'
                OR EXISTS (
                    SELECT 1 FROM mysql.db d
                    WHERE d.User = u.User AND d.Host = u.Host
                        AND d.Select_priv = 'Y'
                        AND d.Insert_priv = 'N' AND d.Update_priv = 'N'
                        AND d.Delete_priv = 'N' AND d.Create_priv = 'N'
                        AND d.Drop_priv = 'N' AND d.Alter_priv = 'N'
                )
                THEN 'Read-Only Users'
            ELSE 'Special Purpose Users'
        END AS group_name,
        u.User AS user,
        u.Host AS host,
        u.account_locked AS account_locked,
        u.password_expired AS password_expired,
        u.password_last_changed AS password_last_changed,
        u.plugin AS plugin
    FROM
        mysql.user u
) g
ORDER BY
    g.group_name, g.user, g.host
