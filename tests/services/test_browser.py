"""Tests for the browser service."""

from unittest.mock import MagicMock, patch

from mydba_tui.services.browser import (
    ColumnInfo,
    IndexInfo,
    IndexSizeInfo,
    ObjectCounts,
    TableInfo,
    get_index_sizes,
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
