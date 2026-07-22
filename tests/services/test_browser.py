"""Tests for the browser service."""

from mydba_tui.services.browser import ObjectCounts


def test_object_counts_defaults() -> None:
    """ObjectCounts should default to all zeros."""
    counts = ObjectCounts()
    assert counts.tables == 0
    assert counts.views == 0
    assert counts.procedures == 0
    assert counts.functions == 0
    assert counts.events == 0
    assert counts.triggers == 0


def test_object_counts_with_values() -> None:
    """ObjectCounts should hold the provided values."""
    counts = ObjectCounts(tables=10, views=3, procedures=5, functions=2, events=1, triggers=4)
    assert counts.tables == 10
    assert counts.views == 3
    assert counts.procedures == 5
    assert counts.functions == 2
    assert counts.events == 1
    assert counts.triggers == 4
