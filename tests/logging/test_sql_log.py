"""Tests for the SQL log."""

from pathlib import Path
from unittest.mock import patch

from mydba_tui.logging.sql_log import collapse_sql, log_sql


class TestCollapseSql:
    """Tests for SQL collapsing into single-line format."""

    def test_single_line_unchanged(self) -> None:
        """A single-line SQL should remain unchanged."""
        sql = "SELECT 1"
        assert collapse_sql(sql) == "SELECT 1"

    def test_multiline_collapsed(self) -> None:
        """Multi-line SQL should collapse to one line."""
        sql = "SELECT\n    table_name\nFROM\n    information_schema.tables"
        assert collapse_sql(sql) == "SELECT table_name FROM information_schema.tables"

    def test_tabs_collapsed(self) -> None:
        """Tabs should be replaced with single space."""
        sql = "SELECT\t\ttable_name\tFROM\ttables"
        assert collapse_sql(sql) == "SELECT table_name FROM tables"

    def test_mixed_whitespace(self) -> None:
        """Combination of spaces, tabs, newlines should all collapse."""
        sql = "  SELECT \n\t  x  \n\t  FROM  \n\t  t  "
        assert collapse_sql(sql) == "SELECT x FROM t"

    def test_empty_string(self) -> None:
        """Empty string should return empty string."""
        assert collapse_sql("") == ""

    def test_only_whitespace(self) -> None:
        """Whitespace-only string should return empty string."""
        assert collapse_sql("   \n\t  ") == ""

    def test_preserves_string_content(self) -> None:
        """SQL string literals are collapsed too (expected — log is for tracing)."""
        sql = "SELECT * FROM t WHERE name = 'hello world'"
        assert collapse_sql(sql) == "SELECT * FROM t WHERE name = 'hello world'"

    def test_real_world_query(self) -> None:
        """A realistic formatted query should collapse correctly."""
        sql = """
            SELECT
                t.table_name,
                t.engine,
                t.table_rows
            FROM
                information_schema.tables t
            WHERE
                t.table_schema = 'payments'
            ORDER BY
                t.table_name
        """
        expected = (
            "SELECT t.table_name, t.engine, t.table_rows "
            "FROM information_schema.tables t "
            "WHERE t.table_schema = 'payments' "
            "ORDER BY t.table_name"
        )
        assert collapse_sql(sql) == expected

    def test_strips_line_comments(self) -> None:
        """SQL comments (-- style) should be removed."""
        sql = "-- Load schemas\nSELECT schema_name\n-- Filter\nFROM schemata"
        assert collapse_sql(sql) == "SELECT schema_name FROM schemata"

    def test_strips_hash_comments(self) -> None:
        """SQL comments (# style) should be removed."""
        sql = "# Load schemas\nSELECT schema_name\n# Filter\nFROM schemata"
        assert collapse_sql(sql) == "SELECT schema_name FROM schemata"

    def test_strips_block_comments(self) -> None:
        """SQL block comments (/* */ style) should be removed."""
        sql = "/* Load schemas */\nSELECT schema_name /* inline */ FROM schemata"
        assert collapse_sql(sql) == "SELECT schema_name FROM schemata"

    def test_strips_multiline_block_comments(self) -> None:
        """Multi-line block comments should be removed."""
        sql = "/*\n * Multi-line\n * comment\n */\nSELECT 1"
        assert collapse_sql(sql) == "SELECT 1"

    def test_strips_comments_from_sql_file(self) -> None:
        """Comments at the start of .sql file content should be stripped."""
        sql = """-- List all schemas on the server.
SELECT
    schema_name
FROM
    information_schema.schemata
ORDER BY
    schema_name"""
        result = collapse_sql(sql)
        assert result.startswith("SELECT")
        assert "--" not in result


class TestLogSql:
    """Tests for writing SQL log entries."""

    def test_creates_log_file(self, tmp_path: Path) -> None:
        """log_sql should create the log file if it does not exist."""
        log_file = tmp_path / "logs" / "sql.log"

        with patch("mydba_tui.logging.sql_log.get_sql_log_path", return_value=log_file):
            log_sql("SELECT 1", 0.005, "test.basic")

        assert log_file.exists()

    def test_log_format(self, tmp_path: Path) -> None:
        """Log entries should follow the expected format."""
        log_file = tmp_path / "logs" / "sql.log"

        with patch("mydba_tui.logging.sql_log.get_sql_log_path", return_value=log_file):
            log_sql("SELECT @@version", 0.023, "server.detection")

        content = log_file.read_text(encoding="utf-8")
        # Format: timestamp | duration | source | sql
        assert "| 0.023s |" in content
        assert "| server.detection |" in content
        assert "| SELECT @@version" in content

    def test_multiline_sql_is_collapsed(self, tmp_path: Path) -> None:
        """Multi-line SQL should be written as a single line."""
        log_file = tmp_path / "logs" / "sql.log"
        sql = "SELECT\n    x\nFROM\n    t"

        with patch("mydba_tui.logging.sql_log.get_sql_log_path", return_value=log_file):
            log_sql(sql, 0.010, "test.collapse")

        content = log_file.read_text(encoding="utf-8")
        lines = content.strip().splitlines()
        assert len(lines) == 1
        assert "SELECT x FROM t" in lines[0]

    def test_appends_multiple_entries(self, tmp_path: Path) -> None:
        """Multiple log_sql calls should append to the same file."""
        log_file = tmp_path / "logs" / "sql.log"

        with patch("mydba_tui.logging.sql_log.get_sql_log_path", return_value=log_file):
            log_sql("SELECT 1", 0.001, "test.first")
            log_sql("SELECT 2", 0.002, "test.second")
            log_sql("SELECT 3", 0.003, "test.third")

        content = log_file.read_text(encoding="utf-8")
        lines = content.strip().splitlines()
        assert len(lines) == 3

    def test_duration_formatting(self, tmp_path: Path) -> None:
        """Duration should be formatted to 3 decimal places."""
        log_file = tmp_path / "logs" / "sql.log"

        with patch("mydba_tui.logging.sql_log.get_sql_log_path", return_value=log_file):
            log_sql("SELECT 1", 1.5, "test.duration")

        content = log_file.read_text(encoding="utf-8")
        assert "1.500s" in content
