"""Tests for the export framework."""

import json
from pathlib import Path

import pytest

from mydba_tui.exporters import (
    export_result_set,
)
from mydba_tui.exporters.csv_exporter import CsvExporter, CsvSemicolonExporter
from mydba_tui.exporters.html_exporter import HtmlExporter
from mydba_tui.exporters.json_exporter import JsonExporter, JsonlExporter
from mydba_tui.exporters.markdown_exporter import MarkdownExporter
from mydba_tui.exporters.sql_exporter import SqlInsertBatchExporter, SqlInsertExporter
from mydba_tui.exporters.tsv_exporter import TsvExporter
from mydba_tui.exporters.xml_exporter import XmlExporter


@pytest.fixture()
def col_names() -> list[str]:
    return ["id", "name", "status"]


@pytest.fixture()
def rows() -> list[tuple[object, ...]]:
    return [
        (1, "Alice", "active"),
        (2, "Bob", None),
        (3, "Charlie", "inactive"),
    ]


# --- CSV ---


def test_csv_export(tmp_path: Path, col_names: list[str], rows: list) -> None:
    """CsvExporter should produce valid CSV with \\N for NULL."""
    path = tmp_path / "test.csv"
    exporter = CsvExporter()
    count = export_result_set(col_names, rows, path, exporter)

    assert count == 3
    content = path.read_text()
    lines = content.strip().split("\n")
    assert lines[0] == "id,name,status"
    assert lines[1] == "1,Alice,active"
    assert "\\N" in lines[2]  # NULL → \N
    assert lines[3] == "3,Charlie,inactive"


def test_csv_semicolon_export(tmp_path: Path, col_names: list[str], rows: list) -> None:
    """CsvSemicolonExporter should use semicolons."""
    path = tmp_path / "test.csv"
    exporter = CsvSemicolonExporter()
    export_result_set(col_names, rows, path, exporter)

    content = path.read_text()
    lines = content.strip().split("\n")
    assert lines[0] == "id;name;status"


# --- TSV ---


def test_tsv_export(tmp_path: Path, col_names: list[str], rows: list) -> None:
    """TsvExporter should produce tab-separated output with \\N for NULL."""
    path = tmp_path / "test.tsv"
    exporter = TsvExporter()
    export_result_set(col_names, rows, path, exporter)

    content = path.read_text()
    lines = content.strip().split("\n")
    assert lines[0] == "id\tname\tstatus"
    assert "\\N" in lines[2]


# --- SQL ---


def test_sql_export(tmp_path: Path, col_names: list[str], rows: list) -> None:
    """SqlInsertExporter should produce INSERT statements."""
    path = tmp_path / "test.sql"
    exporter = SqlInsertExporter(table_name="users")
    count = export_result_set(col_names, rows, path, exporter)

    assert count == 3
    content = path.read_text()
    assert "INSERT INTO `users`" in content
    assert "VALUES (1, 'Alice', 'active')" in content
    assert "NULL" in content


def test_sql_batch_export(tmp_path: Path, col_names: list[str], rows: list) -> None:
    """SqlInsertBatchExporter should produce multi-row INSERTs."""
    path = tmp_path / "test.sql"
    exporter = SqlInsertBatchExporter(table_name="users")
    export_result_set(col_names, rows, path, exporter)

    content = path.read_text()
    assert "INSERT INTO `users`" in content
    assert "VALUES" in content
    # All 3 rows should be in one batch (< 100)
    assert content.count("INSERT") == 1


# --- JSON ---


def test_jsonl_export(tmp_path: Path, col_names: list[str], rows: list) -> None:
    """JsonlExporter should produce one JSON object per line."""
    path = tmp_path / "test.jsonl"
    exporter = JsonlExporter()
    export_result_set(col_names, rows, path, exporter)

    lines = path.read_text().strip().split("\n")
    obj1 = json.loads(lines[0])
    assert obj1 == {"id": 1, "name": "Alice", "status": "active"}
    obj2 = json.loads(lines[1])
    assert obj2["status"] is None


def test_json_export(tmp_path: Path, col_names: list[str], rows: list) -> None:
    """JsonExporter should produce a single JSON array."""
    path = tmp_path / "test.json"
    exporter = JsonExporter()
    export_result_set(col_names, rows, path, exporter)

    data = json.loads(path.read_text())
    assert isinstance(data, list)
    assert len(data) == 3
    assert data[0]["name"] == "Alice"
    assert data[1]["status"] is None


# --- XML ---


def test_xml_export(tmp_path: Path, col_names: list[str], rows: list) -> None:
    """XmlExporter should produce valid XML with resultset/row/field."""
    path = tmp_path / "test.xml"
    exporter = XmlExporter()
    export_result_set(col_names, rows, path, exporter)

    content = path.read_text()
    assert '<?xml version="1.0"' in content
    assert "<resultset>" in content
    assert "</resultset>" in content
    assert '<field name="name">Alice</field>' in content
    assert 'xsi:nil="true"' in content  # NULL field


# --- HTML ---


def test_html_export(tmp_path: Path, col_names: list[str], rows: list) -> None:
    """HtmlExporter should produce an HTML table."""
    path = tmp_path / "test.html"
    exporter = HtmlExporter()
    export_result_set(col_names, rows, path, exporter)

    content = path.read_text()
    assert "<table>" in content
    assert "<th>id</th>" in content
    assert "<td>Alice</td>" in content
    assert 'class="null">NULL</td>' in content


# --- Markdown ---


def test_markdown_export(tmp_path: Path, col_names: list[str], rows: list) -> None:
    """MarkdownExporter should produce a Markdown table."""
    path = tmp_path / "test.md"
    exporter = MarkdownExporter()
    export_result_set(col_names, rows, path, exporter)

    content = path.read_text()
    lines = content.strip().split("\n")
    assert "| id | name | status |" == lines[0]
    assert "| --- | --- | --- |" == lines[1]
    assert "| 1 | Alice | active |" == lines[2]
    assert "NULL" in lines[3]


# --- Safety ---


def test_export_file_exists_error(tmp_path: Path, col_names: list[str], rows: list) -> None:
    """Export should fail if file already exists."""
    path = tmp_path / "existing.csv"
    path.write_text("already here")

    with pytest.raises(FileExistsError):
        export_result_set(col_names, rows, path, CsvExporter())


def test_export_binary_values(tmp_path: Path) -> None:
    """Binary values should be exported as hex."""
    col_names = ["id", "data"]
    rows = [(1, b"\xab\xcd\xef")]

    path = tmp_path / "binary.csv"
    export_result_set(col_names, rows, path, CsvExporter())
    content = path.read_text()
    assert "0xABCDEF" in content


def test_export_special_chars(tmp_path: Path) -> None:
    """Special characters should be escaped in CSV/TSV."""
    col_names = ["id", "text"]
    rows = [(1, "line1\nline2\ttab")]

    path = tmp_path / "special.csv"
    export_result_set(col_names, rows, path, CsvExporter())
    content = path.read_text()
    assert "\\n" in content
    assert "\\t" in content


# --- Auto-discovery ---


def test_auto_discovery_finds_all_exporters() -> None:
    """EXPORTERS registry should contain all defined exporters."""
    from mydba_tui.exporters import EXPORTERS

    expected_keys = {
        "csv",
        "csv_semicolon",
        "tsv",
        "sql",
        "sql_batch",
        "jsonl",
        "json",
        "xml",
        "html",
        "markdown",
    }
    assert expected_keys.issubset(set(EXPORTERS.keys()))


def test_all_exporters_have_required_attributes() -> None:
    """All registered exporters should have name, extension, and format_key."""
    from mydba_tui.exporters import EXPORTERS

    for key, cls in EXPORTERS.items():
        assert cls.name, f"{key} missing name"
        assert cls.extension, f"{key} missing extension"
        assert cls.format_key == key, f"{key} format_key mismatch"
