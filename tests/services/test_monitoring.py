"""Tests for the monitoring snapshot/rate service."""

from typing import Any

from mydba_tui.services.monitoring import Snapshot, fetch_snapshot, rate, sum_rate


class _FakeCursor:
    def __init__(self, script: dict[str, list[tuple[Any, Any]]], *, raise_status: bool) -> None:
        self._script = script
        self._raise_status = raise_status
        self._rows: list[tuple[Any, Any]] = []

    def execute(self, sql: str) -> None:
        if "SHOW GLOBAL STATUS" in sql:
            if self._raise_status:
                raise RuntimeError("no status")
            self._rows = self._script.get("status", [])
        elif "SHOW GLOBAL VARIABLES" in sql:
            self._rows = self._script.get("variables", [])
        else:
            self._rows = []

    def fetchall(self) -> list[tuple[Any, Any]]:
        return self._rows

    def close(self) -> None:
        pass


class _FakeConnection:
    def __init__(
        self, script: dict[str, list[tuple[Any, Any]]], *, raise_status: bool = False
    ) -> None:
        self._script = script
        self._raise_status = raise_status

    def cursor(self, buffered: bool = False) -> _FakeCursor:
        return _FakeCursor(self._script, raise_status=self._raise_status)


def test_fetch_snapshot_maps_status_and_variables() -> None:
    """A snapshot exposes status counters (float) and variables (string)."""
    conn = _FakeConnection(
        {
            "status": [("Queries", "100"), ("Threads_connected", "8")],
            "variables": [("max_connections", "512")],
        }
    )
    snap = fetch_snapshot(conn)  # type: ignore[arg-type]
    assert snap.available is True
    assert snap.gauge("Queries") == 100.0
    assert snap.gauge("threads_connected") == 8.0  # case-insensitive
    assert snap.var("max_connections") == "512"
    assert snap.var_float("max_connections") == 512.0
    assert snap.taken_at > 0


def test_fetch_snapshot_unavailable_when_status_fails() -> None:
    """A failed SHOW GLOBAL STATUS yields an unavailable snapshot."""
    conn = _FakeConnection({}, raise_status=True)
    snap = fetch_snapshot(conn)  # type: ignore[arg-type]
    assert snap.available is False


def test_rate_is_per_second_delta() -> None:
    """rate() = (cur - prev) / elapsed seconds."""
    prev = Snapshot(status={"queries": 100.0}, taken_at=10.0)
    cur = Snapshot(status={"queries": 400.0}, taken_at=20.0)
    assert rate(prev, cur, "Queries") == 30.0  # (400-100)/10


def test_rate_zero_when_counter_resets_or_no_interval() -> None:
    """A counter going backwards (restart) or a zero interval yields 0."""
    prev = Snapshot(status={"queries": 500.0}, taken_at=10.0)
    reset = Snapshot(status={"queries": 5.0}, taken_at=20.0)
    assert rate(prev, reset, "Queries") == 0.0

    same = Snapshot(status={"queries": 600.0}, taken_at=10.0)
    assert rate(prev, same, "Queries") == 0.0  # elapsed == 0


def test_sum_rate_adds_counter_rates() -> None:
    """sum_rate() adds the per-second rates of several counters."""
    prev = Snapshot(status={"a": 0.0, "b": 0.0}, taken_at=0.0)
    cur = Snapshot(status={"a": 10.0, "b": 20.0}, taken_at=10.0)
    assert sum_rate(prev, cur, ("a", "b")) == 3.0  # (10+20)/10
