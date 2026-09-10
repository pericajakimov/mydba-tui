"""Tests for the Performance (sys schema) diagnostics service."""

from typing import Any

from mydba_tui.services.performance import (
    fetch_breakdown,
    fetch_statement_digest_sample,
    fetch_view,
)


class _FakeCursor:
    def __init__(
        self,
        columns: list[str] | None,
        rows: list[tuple[Any, ...]],
        *,
        raise_on_execute: bool = False,
    ) -> None:
        self._columns = columns
        self._rows = rows
        self._raise = raise_on_execute
        self.description = [(c,) for c in columns] if columns else None
        self.executed_params: Any = None

    def execute(self, sql: str, params: Any = None) -> None:
        if self._raise:
            raise RuntimeError("view unavailable")
        self.executed_params = params

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows

    def close(self) -> None:
        pass


class _FakeConnection:
    def __init__(
        self,
        columns: list[str] | None,
        rows: list[tuple[Any, ...]],
        *,
        raise_on_execute: bool = False,
    ) -> None:
        self._columns = columns
        self._rows = rows
        self._raise = raise_on_execute
        self.last_cursor: _FakeCursor | None = None

    def cursor(self, buffered: bool = False) -> _FakeCursor:
        self.last_cursor = _FakeCursor(self._columns, self._rows, raise_on_execute=self._raise)
        return self.last_cursor


def test_fetch_view_returns_columns_and_string_rows() -> None:
    """A summary view maps to a GridData of column headers and string rows."""
    conn = _FakeConnection(
        ["query", "exec_count", "full_scan"],
        [("SELECT 1", 10, 0), ("SELECT 2", 5, 1)],
    )
    grid = fetch_view(conn, "admin/perf/statement_analysis.sql", "test")  # type: ignore[arg-type]
    assert grid.available is True
    assert grid.columns == ["query", "exec_count", "full_scan"]
    # Values are coerced to strings.
    assert grid.rows == [["SELECT 1", "10", "0"], ["SELECT 2", "5", "1"]]
    assert grid.empty is False


def test_fetch_view_unavailable_on_error() -> None:
    """A missing view/privilege yields an unavailable grid, not an exception."""
    conn = _FakeConnection(None, [], raise_on_execute=True)
    grid = fetch_view(conn, "admin/perf/statement_analysis.sql", "test")  # type: ignore[arg-type]
    assert grid.available is False
    assert grid.columns == []
    assert grid.rows == []
    assert grid.empty is True


def test_fetch_view_coerces_none_and_bytes() -> None:
    """None becomes empty string; bytes are decoded."""
    conn = _FakeConnection(["a", "b"], [(None, b"xyz")])
    grid = fetch_view(conn, "admin/perf/statement_analysis.sql", "test")  # type: ignore[arg-type]
    assert grid.rows == [["", "xyz"]]


def test_fetch_breakdown_binds_params() -> None:
    """A keyed breakdown passes its parameters through to execute()."""
    conn = _FakeConnection(["k", "v"], [("x", "1")])
    grid = fetch_breakdown(
        conn,  # type: ignore[arg-type]
        "admin/perf/statement_digest_sample.sql",
        ("abc123",),
        "test",
    )
    assert grid.available is True
    assert conn.last_cursor is not None
    assert conn.last_cursor.executed_params == ("abc123",)


def test_fetch_statement_digest_sample_maps_row() -> None:
    """The digest sample row maps into the typed dataclass by column name."""
    conn = _FakeConnection(
        ["digest_text", "sample_text", "schema_name", "exec_count", "first_seen", "last_seen"],
        [("SELECT ?", "SELECT 42", "shop", 99, "2026-01-01", "2026-01-02")],
    )
    sample = fetch_statement_digest_sample(conn, "deadbeef")  # type: ignore[arg-type]
    assert sample is not None
    assert sample.digest_text == "SELECT ?"
    assert sample.sample_text == "SELECT 42"
    assert sample.schema_name == "shop"
    assert sample.exec_count == "99"


def test_fetch_statement_digest_sample_none_when_missing() -> None:
    """No matching digest row yields None."""
    conn = _FakeConnection(["digest_text"], [])
    assert fetch_statement_digest_sample(conn, "nope") is None  # type: ignore[arg-type]
