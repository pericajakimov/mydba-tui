"""Tests for the browser service."""

from unittest.mock import MagicMock, patch

from mydba_tui.services.browser import (
    ColumnInfo,
    EventInfo,
    ForeignKeyInfo,
    GrantInfo,
    IndexInfo,
    IndexSizeInfo,
    ObjectCounts,
    PartitionInfo,
    RoutineInfo,
    RoutineParam,
    TableInfo,
    TriggerDetailInfo,
    TriggerInfo,
    ViewInfo,
    get_index_sizes,
    get_sample_data,
    get_table_fk_incoming,
    get_table_fk_outgoing,
    get_table_grants,
    get_table_partitions,
    get_table_triggers,
)


def test_object_counts_defaults() -> None:
    """ObjectCounts should default to all zeros."""
    counts = ObjectCounts()
    assert counts.tables == 0
    assert counts.views == 0
    assert counts.procedures == 0
    assert counts.functions == 0
    assert counts.events == 0
    assert counts.triggers == 0


def test_object_counts_with_values() -> None:
    """ObjectCounts should hold the provided values."""
    counts = ObjectCounts(tables=10, views=3, procedures=5, functions=2, events=1, triggers=4)
    assert counts.tables == 10
    assert counts.views == 3
    assert counts.procedures == 5
    assert counts.functions == 2
    assert counts.events == 1
    assert counts.triggers == 4


def test_table_info_defaults() -> None:
    """TableInfo should have sensible defaults."""
    info = TableInfo()
    assert info.name == ""
    assert info.engine == ""
    assert info.row_count == 0
    assert info.auto_increment is None


def test_column_info_defaults() -> None:
    """ColumnInfo should have empty defaults."""
    col = ColumnInfo()
    assert col.position == 0
    assert col.name == ""
    assert col.col_type == ""


def test_index_info_defaults() -> None:
    """IndexInfo should have empty defaults."""
    idx = IndexInfo()
    assert idx.name == ""
    assert idx.non_unique == 0
    assert idx.column == ""
    assert idx.cardinality == 0
    assert idx.visible == "YES"
    assert idx.expression == ""


def test_index_size_info_defaults() -> None:
    """IndexSizeInfo should have empty defaults."""
    info = IndexSizeInfo()
    assert info.name == ""
    assert info.size_bytes == 0


def test_index_size_info_with_values() -> None:
    """IndexSizeInfo should hold provided values."""
    info = IndexSizeInfo(name="PRIMARY", size_bytes=16384)
    assert info.name == "PRIMARY"
    assert info.size_bytes == 16384


@patch("mydba_tui.services.browser.load_sql")
def test_get_index_sizes_returns_dict(mock_load_sql: MagicMock) -> None:
    """get_index_sizes should return a dict mapping index_name to size_bytes."""
    mock_load_sql.return_value = (
        "SELECT index_name, stat_value * 16384 FROM t"
        " WHERE database_name = '{schema}' AND table_name = '{table}'"
    )

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("PRIMARY", 163840),
        ("idx_email", 49152),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_index_sizes(mock_conn, "mydb", "users")

    assert result == {"PRIMARY": 163840, "idx_email": 49152}
    mock_cursor.execute.assert_called_once()
    mock_cursor.close.assert_called_once()


@patch("mydba_tui.services.browser.load_sql")
def test_get_index_sizes_returns_empty_on_error(mock_load_sql: MagicMock) -> None:
    """get_index_sizes should return empty dict when privilege is denied."""
    mock_load_sql.return_value = "SELECT ..."

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = MagicMock(
        execute=MagicMock(side_effect=Exception("Access denied"))
    )

    result = get_index_sizes(mock_conn, "mydb", "users")

    assert result == {}


@patch("mydba_tui.services.browser.load_sql")
def test_get_index_sizes_empty_table(mock_load_sql: MagicMock) -> None:
    """get_index_sizes should return empty dict for table with no indexes."""
    mock_load_sql.return_value = "SELECT ..."

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_index_sizes(mock_conn, "mydb", "empty_table")

    assert result == {}


def test_foreign_key_info_defaults() -> None:
    """ForeignKeyInfo should have sensible defaults."""
    fk = ForeignKeyInfo()
    assert fk.constraint_name == ""
    assert fk.column == ""
    assert fk.referenced_table == ""
    assert fk.referenced_column == ""
    assert fk.ordinal == 1
    assert fk.delete_rule == "NO ACTION"
    assert fk.update_rule == "NO ACTION"
    assert fk.source_table == ""


def test_foreign_key_info_with_values() -> None:
    """ForeignKeyInfo should hold provided values."""
    fk = ForeignKeyInfo(
        constraint_name="fk_order_customer",
        column="customer_id",
        referenced_table="customers",
        referenced_column="id",
        ordinal=1,
        delete_rule="CASCADE",
        update_rule="NO ACTION",
    )
    assert fk.constraint_name == "fk_order_customer"
    assert fk.column == "customer_id"
    assert fk.referenced_table == "customers"
    assert fk.referenced_column == "id"
    assert fk.delete_rule == "CASCADE"


@patch("mydba_tui.services.browser.load_sql")
def test_get_table_fk_outgoing_returns_list(mock_load_sql: MagicMock) -> None:
    """get_table_fk_outgoing should return a list of ForeignKeyInfo."""
    mock_load_sql.return_value = "SELECT ..."

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("fk_order_customer", "customer_id", "customers", "id", 1, "CASCADE", "NO ACTION"),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_table_fk_outgoing(mock_conn, "mydb", "orders")

    assert len(result) == 1
    assert result[0].constraint_name == "fk_order_customer"
    assert result[0].column == "customer_id"
    assert result[0].referenced_table == "customers"
    assert result[0].referenced_column == "id"
    assert result[0].delete_rule == "CASCADE"
    assert result[0].update_rule == "NO ACTION"


@patch("mydba_tui.services.browser.load_sql")
def test_get_table_fk_outgoing_multi_column(mock_load_sql: MagicMock) -> None:
    """get_table_fk_outgoing should handle multi-column FKs."""
    mock_load_sql.return_value = "SELECT ..."

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("fk_composite", "col_a", "target", "ref_a", 1, "RESTRICT", "NO ACTION"),
        ("fk_composite", "col_b", "target", "ref_b", 2, "RESTRICT", "NO ACTION"),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_table_fk_outgoing(mock_conn, "mydb", "orders")

    assert len(result) == 2
    assert result[0].ordinal == 1
    assert result[1].ordinal == 2
    assert result[0].column == "col_a"
    assert result[1].column == "col_b"


@patch("mydba_tui.services.browser.load_sql")
def test_get_table_fk_incoming_returns_list(mock_load_sql: MagicMock) -> None:
    """get_table_fk_incoming should return a list with source_table populated."""
    mock_load_sql.return_value = "SELECT ..."

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("fk_item_order", "order_items", "order_id", "id", 1, "CASCADE", "NO ACTION"),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_table_fk_incoming(mock_conn, "mydb", "orders")

    assert len(result) == 1
    assert result[0].constraint_name == "fk_item_order"
    assert result[0].source_table == "order_items"
    assert result[0].column == "order_id"
    assert result[0].referenced_column == "id"
    assert result[0].delete_rule == "CASCADE"


@patch("mydba_tui.services.browser.load_sql")
def test_get_table_fk_incoming_empty(mock_load_sql: MagicMock) -> None:
    """get_table_fk_incoming should return empty list when no refs exist."""
    mock_load_sql.return_value = "SELECT ..."

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_table_fk_incoming(mock_conn, "mydb", "standalone_table")

    assert result == []


def test_trigger_info_defaults() -> None:
    """TriggerInfo should have empty defaults."""
    trg = TriggerInfo()
    assert trg.name == ""
    assert trg.event == ""
    assert trg.timing == ""
    assert trg.definer == ""
    assert trg.created == ""
    assert trg.body == ""


def test_trigger_info_with_values() -> None:
    """TriggerInfo should hold provided values."""
    trg = TriggerInfo(
        name="trg_audit",
        event="INSERT",
        timing="AFTER",
        definer="root@localhost",
        created="2024-03-15 10:00:00",
        body="BEGIN\n  INSERT INTO log VALUES (NEW.id);\nEND",
    )
    assert trg.name == "trg_audit"
    assert trg.event == "INSERT"
    assert trg.timing == "AFTER"
    assert trg.definer == "root@localhost"
    assert "INSERT INTO log" in trg.body


@patch("mydba_tui.services.browser.load_sql")
def test_get_table_triggers_returns_list(mock_load_sql: MagicMock) -> None:
    """get_table_triggers should return a list of TriggerInfo."""
    mock_load_sql.return_value = "SELECT ..."

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("trg_audit", "INSERT", "BEFORE", "root@localhost", "2024-01-01 00:00:00", "BEGIN END"),
        ("trg_update", "UPDATE", "AFTER", "app@%", "2024-02-01 00:00:00", "BEGIN END"),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_table_triggers(mock_conn, "mydb", "orders")

    assert len(result) == 2
    assert result[0].name == "trg_audit"
    assert result[0].timing == "BEFORE"
    assert result[0].event == "INSERT"
    assert result[1].name == "trg_update"
    assert result[1].timing == "AFTER"


@patch("mydba_tui.services.browser.load_sql")
def test_get_table_triggers_empty(mock_load_sql: MagicMock) -> None:
    """get_table_triggers should return empty list when no triggers exist."""
    mock_load_sql.return_value = "SELECT ..."

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_table_triggers(mock_conn, "mydb", "simple_table")

    assert result == []


def test_partition_info_defaults() -> None:
    """PartitionInfo should have sensible defaults."""
    p = PartitionInfo()
    assert p.name == ""
    assert p.method == ""
    assert p.expression == ""
    assert p.description == ""
    assert p.ordinal == 0
    assert p.row_count == 0
    assert p.data_size == 0
    assert p.index_size == 0


def test_partition_info_with_values() -> None:
    """PartitionInfo should hold provided values."""
    p = PartitionInfo(
        name="p_2024",
        method="RANGE",
        expression="YEAR(created_at)",
        description="2024",
        ordinal=1,
        row_count=5000,
        data_size=1048576,
        index_size=262144,
    )
    assert p.name == "p_2024"
    assert p.method == "RANGE"
    assert p.expression == "YEAR(created_at)"
    assert p.description == "2024"
    assert p.row_count == 5000
    assert p.data_size == 1048576


@patch("mydba_tui.services.browser.load_sql")
def test_get_table_partitions_returns_list(mock_load_sql: MagicMock) -> None:
    """get_table_partitions should return a list of PartitionInfo."""
    mock_load_sql.return_value = "SELECT ..."

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("p_2023", "RANGE", "YEAR(dt)", "2023", 1, 1000, 524288, 131072),
        ("p_2024", "RANGE", "YEAR(dt)", "2024", 2, 5000, 1048576, 262144),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_table_partitions(mock_conn, "mydb", "events")

    assert len(result) == 2
    assert result[0].name == "p_2023"
    assert result[0].method == "RANGE"
    assert result[0].description == "2023"
    assert result[0].row_count == 1000
    assert result[1].name == "p_2024"
    assert result[1].ordinal == 2


@patch("mydba_tui.services.browser.load_sql")
def test_get_table_partitions_empty(mock_load_sql: MagicMock) -> None:
    """get_table_partitions should return empty list for non-partitioned tables."""
    mock_load_sql.return_value = "SELECT ..."

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_table_partitions(mock_conn, "mydb", "simple_table")

    assert result == []


def test_grant_info_defaults() -> None:
    """GrantInfo should have empty defaults."""
    g = GrantInfo()
    assert g.user == ""
    assert g.host == ""
    assert g.grant_level == ""
    assert g.privileges == ""


def test_grant_info_with_values() -> None:
    """GrantInfo should hold provided values."""
    g = GrantInfo(
        user="app_user",
        host="10.0.0.%",
        grant_level="SCHEMA",
        privileges="Select,Insert,Update",
    )
    assert g.user == "app_user"
    assert g.host == "10.0.0.%"
    assert g.grant_level == "SCHEMA"
    assert g.privileges == "Select,Insert,Update"


@patch("mydba_tui.services.browser.load_sql")
def test_get_table_grants_returns_list(mock_load_sql: MagicMock) -> None:
    """get_table_grants should return a list of GrantInfo."""
    mock_load_sql.return_value = "SELECT ..."

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("admin", "localhost", "GLOBAL", "SELECT,INSERT,UPDATE,DELETE"),
        ("reader", "%", "SCHEMA", "SELECT"),
        ("app", "%", "TABLE", "Select,Insert"),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_table_grants(mock_conn, "mydb", "orders")

    assert len(result) == 3
    assert result[0].user == "admin"
    assert result[0].grant_level == "GLOBAL"
    assert result[0].privileges == "SELECT,INSERT,UPDATE,DELETE"
    assert result[1].grant_level == "SCHEMA"
    assert result[2].grant_level == "TABLE"


@patch("mydba_tui.services.browser.load_sql")
def test_get_table_grants_returns_empty_on_error(mock_load_sql: MagicMock) -> None:
    """get_table_grants should return empty list on privilege error."""
    mock_load_sql.return_value = "SELECT ..."

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = MagicMock(
        execute=MagicMock(side_effect=Exception("Access denied"))
    )

    result = get_table_grants(mock_conn, "mydb", "orders")

    assert result == []


@patch("mydba_tui.services.browser.load_sql")
def test_get_table_grants_empty(mock_load_sql: MagicMock) -> None:
    """get_table_grants should return empty list when no grants exist."""
    mock_load_sql.return_value = "SELECT ..."

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    result = get_table_grants(mock_conn, "mydb", "no_grants_table")

    assert result == []


@patch("mydba_tui.services.browser.log_sql")
def test_get_sample_data_with_pk(mock_log: MagicMock) -> None:
    """get_sample_data should order by PK and return formatted strings."""
    columns = [
        ColumnInfo(position=1, name="id", col_type="int", key="PRI"),
        ColumnInfo(position=2, name="name", col_type="varchar(100)"),
    ]

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        (1, "Alice"),
        (2, "Bob"),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    col_names, rows = get_sample_data(
        mock_conn, "mydb", "users", columns=columns, order="ASC", limit=5
    )

    assert col_names == ["id", "name"]
    assert len(rows) == 2
    assert rows[0] == ["1", "Alice"]
    assert rows[1] == ["2", "Bob"]
    data_sql = mock_cursor.execute.call_args[0][0]
    assert "ORDER BY `id` ASC" in data_sql
    assert "LIMIT 5" in data_sql
    assert "SELECT *" in data_sql


@patch("mydba_tui.services.browser.log_sql")
def test_get_sample_data_no_pk(mock_log: MagicMock) -> None:
    """get_sample_data should work without PK (no ORDER BY)."""
    columns = [
        ColumnInfo(position=1, name="col1", col_type="int"),
        ColumnInfo(position=2, name="col2", col_type="varchar(50)"),
    ]

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(1, "test")]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    col_names, rows = get_sample_data(
        mock_conn, "mydb", "heap_table", columns=columns, order="DESC", limit=5
    )

    assert col_names == ["col1", "col2"]
    assert len(rows) == 1
    data_sql = mock_cursor.execute.call_args[0][0]
    assert "ORDER BY" not in data_sql
    assert "LIMIT 5" in data_sql


@patch("mydba_tui.services.browser.log_sql")
def test_get_sample_data_binary_columns(mock_log: MagicMock) -> None:
    """get_sample_data should format binary values client-side."""
    columns = [
        ColumnInfo(position=1, name="id", col_type="int", key="PRI"),
        ColumnInfo(position=2, name="uuid", col_type="binary(16)"),
        ColumnInfo(position=3, name="payload", col_type="longblob"),
    ]

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        (1, b"\xab\xcd\xef\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d", b"x" * 100),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    col_names, rows = get_sample_data(mock_conn, "mydb", "blobs", columns=columns, order="ASC")

    assert col_names == ["id", "uuid", "payload"]
    assert rows[0][1] == "0xABCDEF0102030405060708090A0B0C0D"  # 16 bytes → hex
    assert rows[0][2] == "<binary>"  # > 16 bytes → <binary>


@patch("mydba_tui.services.browser.log_sql")
def test_get_sample_data_text_truncation(mock_log: MagicMock) -> None:
    """get_sample_data should truncate text values at 100 chars client-side."""
    columns = [
        ColumnInfo(position=1, name="id", col_type="int", key="PRI"),
        ColumnInfo(position=2, name="body", col_type="text"),
    ]

    long_text = "a" * 150

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(1, long_text)]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    col_names, rows = get_sample_data(mock_conn, "mydb", "posts", columns=columns, order="ASC")

    assert col_names == ["id", "body"]
    assert rows[0][1] == "a" * 100 + "..."
    assert len(rows[0][1]) == 103


@patch("mydba_tui.services.browser.log_sql")
def test_get_sample_data_null_values(mock_log: MagicMock) -> None:
    """get_sample_data should format NULL values as 'NULL' string."""
    columns = [
        ColumnInfo(position=1, name="id", col_type="int", key="PRI"),
        ColumnInfo(position=2, name="email", col_type="varchar(255)"),
    ]

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(1, None)]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    col_names, rows = get_sample_data(mock_conn, "mydb", "users", columns=columns, order="ASC")

    assert rows[0][1] == "NULL"


@patch("mydba_tui.services.browser.log_sql")
def test_get_sample_data_empty_table(mock_log: MagicMock) -> None:
    """get_sample_data should return empty rows for empty table."""
    columns = [
        ColumnInfo(position=1, name="id", col_type="int", key="PRI"),
        ColumnInfo(position=2, name="name", col_type="varchar(50)"),
    ]

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    col_names, rows = get_sample_data(mock_conn, "mydb", "empty_table", columns=columns)

    assert col_names == ["id", "name"]
    assert rows == []


# --- View, Routine, Trigger, Event dataclass tests ---


def test_view_info_defaults() -> None:
    """ViewInfo should have empty defaults."""
    v = ViewInfo()
    assert v.schema == ""
    assert v.name == ""
    assert v.definition == ""
    assert v.check_option == "NONE"
    assert v.is_updatable == ""
    assert v.definer == ""
    assert v.security_type == ""


def test_routine_info_defaults() -> None:
    """RoutineInfo should have empty defaults."""
    r = RoutineInfo()
    assert r.schema == ""
    assert r.name == ""
    assert r.routine_type == ""
    assert r.return_type == ""
    assert r.definition == ""
    assert r.is_deterministic == ""


def test_routine_param_defaults() -> None:
    """RoutineParam should have empty defaults."""
    p = RoutineParam()
    assert p.ordinal == 0
    assert p.mode == ""
    assert p.name == ""
    assert p.data_type == ""


def test_trigger_detail_info_defaults() -> None:
    """TriggerDetailInfo should have empty defaults."""
    t = TriggerDetailInfo()
    assert t.schema == ""
    assert t.name == ""
    assert t.event == ""
    assert t.table_name == ""
    assert t.timing == ""
    assert t.body == ""
    assert t.definer == ""


def test_event_info_defaults() -> None:
    """EventInfo should have empty defaults."""
    e = EventInfo()
    assert e.schema == ""
    assert e.name == ""
    assert e.event_type == ""
    assert e.status == ""
    assert e.definition == ""
    assert e.definer == ""
    assert e.interval_value == ""
