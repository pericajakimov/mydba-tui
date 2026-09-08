-- Active InnoDB transactions, joined to the process list for user/host/db.
-- Called from: services/transactions.py → fetch_transactions()
-- Age is computed server-side as seconds since the transaction started.
SELECT
    t.trx_id AS trx_id,
    t.trx_mysql_thread_id AS conn_id,
    p.USER AS user,
    p.HOST AS host,
    p.DB AS db,
    t.trx_state AS state,
    t.trx_started AS started,
    TIMESTAMPDIFF(SECOND, t.trx_started, NOW()) AS age_seconds,
    t.trx_rows_locked AS rows_locked,
    t.trx_query AS query
FROM
    information_schema.innodb_trx t
    LEFT JOIN information_schema.processlist p
        ON p.ID = t.trx_mysql_thread_id
ORDER BY
    age_seconds DESC
