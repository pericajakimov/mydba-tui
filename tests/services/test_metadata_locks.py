"""Tests for the metadata lock waits service."""

from typing import Any

from mydba_tui.services.metadata_locks import fetch_metadata_lock_waits

_COLS = [
    "wait_age_secs",
    "object_schema",
    "object_name",
    "waiting_pid",
    "waiting_account",
    "waiting_lock_type",
    "waiting_query",
    "blocking_pid",
    "blocking_account",
    "blocking_lock_type",
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


def test_fetch_metadata_lock_waits_maps_fields() -> None:
    """A metadata-lock row maps to a MetadataLockWait."""
    row = (
        45,
        "shop",
        "orders",
        101,
        "app@10.0.0.1",
        "EXCLUSIVE",
        "ALTER TABLE orders ADD COLUMN x INT",
        202,
        "etl@10.0.0.2",
        "SHARED_READ",
    )
    result = fetch_metadata_lock_waits(_FakeConnection([row]))  # type: ignore[arg-type]
    assert len(result) == 1
    m = result[0]
    assert m.wait_age_secs == 45
    assert m.object_schema == "shop"
    assert m.object_name == "orders"
    assert m.waiting_pid == 101
    assert m.waiting_account == "app@10.0.0.1"
    assert m.waiting_lock_type == "EXCLUSIVE"
    assert m.blocking_pid == 202
    assert m.blocking_account == "etl@10.0.0.2"


def test_fetch_metadata_lock_waits_empty_when_unavailable() -> None:
    """A sys-schema error yields an empty list (best-effort)."""
    conn = _FakeConnection([], raise_on_execute=True)
    assert fetch_metadata_lock_waits(conn) == []  # type: ignore[arg-type]
