-- Per-index size estimates from InnoDB internal statistics.
-- Called from: services/browser.py → get_index_sizes()
-- Returns one row per index with estimated size in bytes.
-- Requires SELECT privilege on mysql.innodb_index_stats.
-- Falls back gracefully if privilege is missing.
SELECT
    index_name,
    stat_value * @@innodb_page_size AS size_bytes
FROM
    mysql.innodb_index_stats
WHERE
    database_name = '{schema}'
    AND table_name = '{table}'
    AND stat_name = 'size'
ORDER BY
    index_name
