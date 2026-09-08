"""Tests for the global variables service."""

from typing import Any

from mydba_tui.services.variables import fetch_variables


class _FakeCursor:
    def __init__(self, rows: list[tuple[Any, Any]]) -> None:
        self._rows = rows
        self.description = [("Variable_name",), ("Value",)]

    def execute(self, sql: str) -> None:  # noqa: D401 - test stub
        self._sql = sql

    def fetchall(self) -> list[tuple[Any, Any]]:
        return self._rows

    def close(self) -> None:
        pass


class _FakeConnection:
    def __init__(self, rows: list[tuple[Any, Any]]) -> None:
        self._rows = rows

    def cursor(self, buffered: bool = False) -> _FakeCursor:
        return _FakeCursor(self._rows)


def test_fetch_variables_sorted_by_name() -> None:
    """Variables are returned sorted case-insensitively by name."""
    conn = _FakeConnection(
        [
            ("version", "8.4.0"),
            ("Max_connections", "151"),
            ("autocommit", "ON"),
        ]
    )
    result = fetch_variables(conn)  # type: ignore[arg-type]
    names = [n for n, _ in result]
    assert names == ["autocommit", "Max_connections", "version"]


def test_fetch_variables_coerces_none_and_bytes() -> None:
    """None values become empty strings; bytes are decoded."""
    conn = _FakeConnection(
        [
            ("some_null", None),
            ("some_bytes", b"abc"),
        ]
    )
    result = dict(fetch_variables(conn))  # type: ignore[arg-type]
    assert result["some_null"] == ""
    assert result["some_bytes"] == "abc"
