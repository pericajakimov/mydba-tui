"""Tests for the lock waits service."""

from typing import Any

from mydba_tui.services.locks import fetch_lock_waits

_COLS = [
    "wait_age_secs",
    "locked_schema",
    "locked_table",
    "locked_type",
    "waiting_pid",
    "waiting_user",
    "waiting_host",
    "waiting_lock_mode",
    "waiting_query",
    "blocking_pid",
    "blocking_user",
    "blocking_host",
    "blocking_lock_mode",
    "blocking_query",
]


class _FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]], raise_on_execute: bool = False) -> None:
        self._rows = rows
        self._raise = raise_on_execute
        self.description = [(c,) for c in _COLS]

    def execute(self, sql: str) -> None:
        if self._raise:
            raise RuntimeError("sys schema not installed")

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows

    def close(self) -> None:
        pass


class _FakeConnection:
    def __init__(self, rows: list[tuple[Any, ...]], raise_on_execute: bool = False) -> None:
        self._rows = rows
        self._raise = raise_on_execute

    def cursor(self, buffered: bool = False) -> _FakeCursor:
        return _FakeCursor(self._rows, self._raise)


def test_fetch_lock_waits_maps_fields_and_strips_host() -> None:
    """A lock-wait row maps to a LockWait with host ports stripped."""
    row = (
        30,
        "shop",
        "orders",
        "RECORD",
        101,
        "app",
        "10.0.0.1:5000",
        "X",
        "UPDATE orders SET x=1",
        202,
        "etl",
        "10.0.0.2:6000",
        "X",
        "SELECT * FROM orders FOR UPDATE",
    )
    result = fetch_lock_waits(_FakeConnection([row]))  # type: ignore[arg-type]
    assert len(result) == 1
    lw = result[0]
    assert lw.wait_age_secs == 30
    assert lw.locked_table == "orders"
    assert lw.waiting_pid == 101
    assert lw.waiting_host == "10.0.0.1"
    assert lw.blocking_pid == 202
    assert lw.blocking_host == "10.0.0.2"
    assert lw.blocking_query == "SELECT * FROM orders FOR UPDATE"


def test_fetch_lock_waits_empty_when_unavailable() -> None:
    """A sys-schema error yields an empty list (best-effort)."""
    conn = _FakeConnection([], raise_on_execute=True)
    assert fetch_lock_waits(conn) == []  # type: ignore[arg-type]


def test_fetch_lock_waits_handles_idle_blocker() -> None:
    """A NULL blocking query (idle blocker) becomes an empty string."""
    row = (
        5,
        "shop",
        "orders",
        "RECORD",
        101,
        "app",
        "10.0.0.1",
        "X",
        "UPDATE orders SET x=1",
        202,
        "etl",
        "10.0.0.2",
        "X",
        None,
    )
    result = fetch_lock_waits(_FakeConnection([row]))  # type: ignore[arg-type]
    assert result[0].blocking_query == ""
