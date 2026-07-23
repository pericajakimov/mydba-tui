"""Tests for the browser service."""

from mydba_tui.services.browser import ColumnInfo, IndexInfo, ObjectCounts, TableInfo


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
