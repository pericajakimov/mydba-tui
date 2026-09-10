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


def test_render_timeseries_empty_and_no_room() -> None:
    """The framed renderer needs room and data."""
    from mydba_tui.renderers.chart import render_timeseries

    # No room (too narrow) -> empty.
    assert render_timeseries([1.0], 5, 4, 5, 1800).plain == ""
    # Room but no data -> a framed, blank chart (axis present, no plotted dots).
    out = render_timeseries([], 40, 4, 5, 1800)
    assert "now" in out.plain
    assert "└" in out.plain


def test_render_timeseries_fixed_window_axis_labels() -> None:
    """The x-axis shows the fixed window span on the left and 'now' on the right."""
    from mydba_tui.renderers.chart import render_timeseries

    out = render_timeseries([1.0, 2.0, 3.0], width=50, height=5, interval=5, window_seconds=1800)
    text = out.plain
    assert "-30m" in text  # 1800s window, regardless of sample count
    assert "now" in text


def test_render_timeseries_fills_from_the_right() -> None:
    """With few samples in a large window, plotted dots hug the right edge."""
    from mydba_tui.renderers.chart import render_timeseries

    # 2 samples, 30-min window at 5s -> only the rightmost columns are filled.
    out = render_timeseries([5.0, 9.0], width=40, height=4, interval=5, window_seconds=1800)
    body = [ln for ln in out.plain.split("\n") if "⠀" in ln or any(ord(c) > 0x2800 for c in ln)]
    # Find any row with a plotted (non-blank) braille cell, and confirm the
    # last such cell is in the right half of the chart area.
    found_right = False
    for line in body:
        cells = [c for c in line if 0x2800 <= ord(c) <= 0x28FF]
        plotted = [i for i, c in enumerate(cells) if ord(c) > 0x2800]
        if plotted:
            assert max(plotted) >= len(cells) // 2
            found_right = True
    assert found_right


def test_render_timeseries_y_axis_uses_value_fmt_and_unit() -> None:
    """The y-axis top/bottom labels use the provided formatter and unit."""
    from mydba_tui.renderers.chart import render_timeseries

    out = render_timeseries(
        [10.0, 20.0],
        width=50,
        height=5,
        interval=5,
        window_seconds=1800,
        unit="s",
        y_max=20.0,
        value_fmt=lambda v: f"{int(v)}",
    )
    text = out.plain
    assert "20s" in text  # ceiling label
    assert "0s" in text  # floor label
