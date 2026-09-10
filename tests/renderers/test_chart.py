"""Tests for the braille line-chart renderer."""

from __future__ import annotations

from rich.text import Text

from mydba_tui.renderers.chart import braille_line_chart


def test_empty_series_returns_empty_text() -> None:
    """No data renders nothing."""
    assert braille_line_chart([], 20, 4).plain == ""


def test_degenerate_size_returns_empty_text() -> None:
    """A chart with no room renders nothing."""
    assert braille_line_chart([1.0, 2.0], 1, 0).plain == ""


def test_series_renders_braille_grid() -> None:
    """A series renders `height` lines of `width` braille cells."""
    chart = braille_line_chart([0.0, 5.0, 2.0, 8.0, 3.0], width=20, height=4, color="cyan")
    assert isinstance(chart, Text)
    lines = chart.plain.rstrip("\n").split("\n")
    assert len(lines) == 4
    # Every cell is a braille character (U+2800..U+28FF).
    for line in lines:
        assert len(line) == 20
        assert all(0x2800 <= ord(ch) <= 0x28FF for ch in line)
    # Something was actually plotted (not an all-blank grid).
    assert any(ord(ch) > 0x2800 for ch in chart.plain if ch != "\n")


def test_flat_series_stays_within_bounds() -> None:
    """A constant series with a fixed y_max still renders cleanly."""
    chart = braille_line_chart([4.0, 4.0, 4.0], width=10, height=3, y_max=10.0)
    lines = chart.plain.rstrip("\n").split("\n")
    assert len(lines) == 3
