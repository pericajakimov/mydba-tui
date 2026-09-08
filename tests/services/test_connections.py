"""Tests for the connection statistics service."""

from unittest.mock import patch

from mydba_tui.services.connections import fetch_connection_stats
from mydba_tui.services.processlist import ProcessRow


def _proc(user: str, host: str) -> ProcessRow:
    return ProcessRow(
        id=1,
        user=user,
        host=host,
        db="",
        command="Query",
        time=0,
        state="",
        program="",
        info="",
    )


def test_groups_by_user_and_host() -> None:
    """Connections are grouped by (user, host) with counts."""
    processes = [
        _proc("app", "10.0.0.1"),
        _proc("app", "10.0.0.1"),
        _proc("app", "10.0.0.2"),
        _proc("reporting", "10.0.0.5"),
    ]
    with patch("mydba_tui.services.connections.fetch_processes", return_value=processes):
        stats = fetch_connection_stats(object(), None)  # type: ignore[arg-type]

    as_tuples = [(s.user, s.host, s.count) for s in stats]
    assert ("app", "10.0.0.1", 2) in as_tuples
    assert ("app", "10.0.0.2", 1) in as_tuples
    assert ("reporting", "10.0.0.5", 1) in as_tuples
    assert len(stats) == 3


def test_sorted_by_count_desc() -> None:
    """Groups are sorted by count descending."""
    processes = [
        _proc("a", "h1"),
        _proc("b", "h2"),
        _proc("b", "h2"),
        _proc("b", "h2"),
    ]
    with patch("mydba_tui.services.connections.fetch_processes", return_value=processes):
        stats = fetch_connection_stats(object(), None)  # type: ignore[arg-type]

    assert stats[0].user == "b"
    assert stats[0].count == 3
    assert stats[-1].count == 1


def test_empty_process_list() -> None:
    """No processes yields no stats."""
    with patch("mydba_tui.services.connections.fetch_processes", return_value=[]):
        stats = fetch_connection_stats(object(), None)  # type: ignore[arg-type]
    assert stats == []
