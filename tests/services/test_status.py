"""Tests for the global status service."""

from typing import Any

from mydba_tui.services.status import fetch_status


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


def test_fetch_status_sorted_by_name() -> None:
    """Status counters are returned sorted case-insensitively by name."""
    conn = _FakeConnection(
        [
            ("Uptime", "12345"),
            ("Aborted_clients", "0"),
            ("Threads_connected", "8"),
        ]
    )
    result = fetch_status(conn)  # type: ignore[arg-type]
    names = [n for n, _ in result]
    assert names == ["Aborted_clients", "Threads_connected", "Uptime"]


def test_fetch_status_coerces_none_and_bytes() -> None:
    """None values become empty strings; bytes are decoded."""
    conn = _FakeConnection([("x_null", None), ("x_bytes", b"42")])
    result = dict(fetch_status(conn))  # type: ignore[arg-type]
    assert result["x_null"] == ""
    assert result["x_bytes"] == "42"
