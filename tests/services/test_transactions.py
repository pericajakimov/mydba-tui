"""Tests for the transactions service."""

from typing import Any

from mydba_tui.services.transactions import fetch_statement_history, fetch_transactions


class _FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows
        self.description = [
            ("trx_id",),
            ("conn_id",),
            ("user",),
            ("host",),
            ("db",),
            ("state",),
            ("started",),
            ("age_seconds",),
            ("rows_locked",),
            ("query",),
        ]

    def execute(self, sql: str) -> None:  # noqa: D401 - test stub
        self._sql = sql

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows

    def close(self) -> None:
        pass


class _FakeConnection:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def cursor(self, buffered: bool = False) -> _FakeCursor:
        return _FakeCursor(self._rows)


def _row(
    trx_id: str,
    conn_id: int,
    user: str,
    host: str,
    age: int,
    query: str,
) -> tuple[Any, ...]:
    return (trx_id, conn_id, user, host, "shop", "RUNNING", "2026-01-01", age, 5, query)


def test_fetch_transactions_maps_fields_and_strips_host_port() -> None:
    """Fields map correctly and the client port is stripped from host."""
    conn = _FakeConnection([_row("421", 100, "app", "10.0.0.1:44556", 30, "UPDATE t SET x=1")])
    result = fetch_transactions(conn)  # type: ignore[arg-type]
    assert len(result) == 1
    trx = result[0]
    assert trx.trx_id == "421"
    assert trx.conn_id == 100
    assert trx.user == "app"
    assert trx.host == "10.0.0.1"
    assert trx.age_seconds == 30
    assert trx.rows_locked == 5
    assert trx.query == "UPDATE t SET x=1"


def test_fetch_transactions_handles_null_user_host() -> None:
    """A transaction with no matching process row yields empty user/host."""
    conn = _FakeConnection([("999", 0, None, None, None, "RUNNING", "2026-01-01", 0, 0, None)])
    result = fetch_transactions(conn)  # type: ignore[arg-type]
    trx = result[0]
    assert trx.user == ""
    assert trx.host == ""
    assert trx.query == ""
    assert trx.conn_id == 0


class _HistoryCursor:
    def __init__(self, rows: list[tuple[Any, ...]], raise_on_execute: bool = False) -> None:
        self._rows = rows
        self._raise = raise_on_execute

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        if self._raise:
            raise RuntimeError("performance_schema disabled")

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows

    def close(self) -> None:
        pass


class _HistoryConnection:
    def __init__(self, rows: list[tuple[Any, ...]], raise_on_execute: bool = False) -> None:
        self._rows = rows
        self._raise = raise_on_execute

    def cursor(self, buffered: bool = False) -> _HistoryCursor:
        return _HistoryCursor(self._rows, self._raise)


def test_statement_history_maps_rows() -> None:
    """History rows map to entries with sql and duration."""
    conn = _HistoryConnection(
        [
            ("SELECT 1", 1500.0, 20),
            ("UPDATE t SET x=1", 3200.5, 19),
        ]
    )
    entries = fetch_statement_history(conn, 100)  # type: ignore[arg-type]
    assert [e.sql for e in entries] == ["SELECT 1", "UPDATE t SET x=1"]
    assert entries[0].duration_ms == 1500.0


def test_statement_history_skips_blank_sql() -> None:
    """Blank SQL_TEXT rows are skipped."""
    conn = _HistoryConnection([("", 0, 1), ("SELECT 2", 10.0, 2)])
    entries = fetch_statement_history(conn, 100)  # type: ignore[arg-type]
    assert [e.sql for e in entries] == ["SELECT 2"]


def test_statement_history_empty_for_zero_conn_id() -> None:
    """conn_id <= 0 returns no history without querying."""
    conn = _HistoryConnection([("SELECT 1", 0, 1)])
    assert fetch_statement_history(conn, 0) == []  # type: ignore[arg-type]


def test_statement_history_graceful_on_error() -> None:
    """A perf_schema error yields an empty list, not an exception."""
    conn = _HistoryConnection([], raise_on_execute=True)
    assert fetch_statement_history(conn, 100) == []  # type: ignore[arg-type]
