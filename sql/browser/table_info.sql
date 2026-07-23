-- General table information for the metadata view.
-- Called from: services/browser.py → get_table_info()
-- Shows engine, size, row count, timestamps, and other table properties.
SELECT
    table_name,
    engine,
    table_rows,
    avg_row_length,
    data_length,
    index_length,
    data_free,
    auto_increment,
    create_time,
    update_time,
    check_time,
    table_collation,
    table_comment,
    row_format,
    create_options
FROM
    information_schema.tables
WHERE
    table_schema = '{schema}'
    AND table_name = '{table}'
