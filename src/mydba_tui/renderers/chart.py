"""
Braille line-chart renderer.

Renders a numeric series as a compact line chart using Unicode braille
characters (each cell packs a 2x4 dot grid, giving sub-character resolution).
Produces a Rich Text object suitable for a Static widget — no external
charting dependency. Reused by the Replication lag graph and, later, the
Monitoring page.
"""

from __future__ import annotations

from collections.abc import Callable

from rich.text import Text

# Braille dot bit positions within a cell (Unicode U+2800 base). Columns are
# 2 wide, rows are 4 tall. The bit for (col, row):
#   col 0: rows -> 0x01, 0x02, 0x04, 0x40 (top -> bottom)
#   col 1: rows -> 0x08, 0x10, 0x20, 0x80 (top -> bottom)
_BRAILLE_DOTS = (
    (0x01, 0x02, 0x04, 0x40),
    (0x08, 0x10, 0x20, 0x80),
)


def braille_line_chart(
    values: list[float],
    width: int,
    height: int,
    *,
    color: str = "cyan",
    y_max: float | None = None,
) -> Text:
    """Render values as a braille line chart.

    Args:
        values: The series (oldest first). Rendered left to right.
        width: Chart width in terminal cells (each cell = 2 dot columns).
        height: Chart height in terminal cells (each cell = 4 dot rows).
        color: Line colour.
        y_max: Optional fixed top of the y-axis; defaults to max(values).

    Returns:
        A Rich Text chart (empty Text if there is nothing to render).
    """
    if not values or width < 2 or height < 1:
        return Text()

    dot_cols = width * 2
    dot_rows = height * 4

    top = y_max if y_max is not None else max(values)
    if top <= 0:
        top = 1.0

    # Resample the series to one value per dot-column (nearest sample).
    n = len(values)
    sampled: list[float] = []
    for col in range(dot_cols):
        idx = round(col * (n - 1) / max(dot_cols - 1, 1)) if n > 1 else 0
        sampled.append(values[idx])

    # cell grid: each cell holds a braille bitmask.
    grid = [[0 for _ in range(width)] for _ in range(height)]

    def _plot(dot_col: int, value: float) -> None:
        # Map value -> dot row (0 at top). Clamp into range.
        frac = max(0.0, min(1.0, value / top))
        dot_row_from_top = int(round((1.0 - frac) * (dot_rows - 1)))
        cell_col = dot_col // 2
        cell_row = dot_row_from_top // 4
        sub_col = dot_col % 2
        sub_row = dot_row_from_top % 4
        if 0 <= cell_row < height and 0 <= cell_col < width:
            grid[cell_row][cell_col] |= _BRAILLE_DOTS[sub_col][sub_row]

    # Plot each sampled point; connect consecutive points vertically so the
    # line reads as continuous rather than as dots.
    prev_row: int | None = None
    for dot_col, value in enumerate(sampled):
        frac = max(0.0, min(1.0, value / top))
        row = int(round((1.0 - frac) * (dot_rows - 1)))
        _plot(dot_col, value)
        if prev_row is not None:
            lo, hi = sorted((prev_row, row))
            for r in range(lo, hi + 1):
                cell_col = dot_col // 2
                cell_row = r // 4
                if 0 <= cell_row < height and 0 <= cell_col < width:
                    grid[cell_row][cell_col] |= _BRAILLE_DOTS[dot_col % 2][r % 4]
        prev_row = row

    text = Text()
    for grid_row in grid:
        line = "".join(chr(0x2800 + mask) for mask in grid_row)
        text.append(line, style=color)
        text.append("\n")
    return text


def _format_ago(seconds: int) -> str:
    """Format an elapsed duration as a compact relative label (e.g. 90s, 3m, 2h)."""
    if seconds < 90:
        return f"{seconds}s"
    minutes = seconds / 60
    if minutes < 90:
        return f"{round(minutes)}m"
    return f"{round(minutes / 60)}h"


def _plot_grid(
    grid: list[list[int]],
    plots: list[tuple[int, int]],
    width: int,
    height: int,
) -> None:
    """Plot (dot_col, dot_row_from_top) points into a braille cell grid.

    Consecutive points are connected vertically so the series reads as a
    continuous line rather than dots.
    """

    def _set(dot_col: int, dot_row: int) -> None:
        cell_col = dot_col // 2
        cell_row = dot_row // 4
        if 0 <= cell_row < height and 0 <= cell_col < width:
            grid[cell_row][cell_col] |= _BRAILLE_DOTS[dot_col % 2][dot_row % 4]

    prev: tuple[int, int] | None = None
    for dot_col, dot_row in plots:
        _set(dot_col, dot_row)
        if prev is not None and prev[0] == dot_col - 1:
            lo, hi = sorted((prev[1], dot_row))
            for r in range(lo, hi + 1):
                _set(dot_col, r)
        prev = (dot_col, dot_row)


def render_timeseries(
    series: list[float],
    width: int,
    height: int,
    interval: int,
    window_seconds: int,
    *,
    unit: str = "",
    color: str = "cyan",
    y_max: float | None = None,
    value_fmt: Callable[[float], str] | None = None,
) -> Text:
    """Render a framed time-series chart over a fixed time window.

    The x-axis always spans ``window_seconds`` (e.g. 30 minutes). The newest
    sample sits at the right edge ("now") and the line fills from the right
    toward the left as history accumulates — the window does not grow. A
    left gutter shows the y-axis max/min; a bottom row shows the x-axis with
    ``-<window>`` on the left and ``now`` on the right.

    Args:
        series: Sample values, oldest first (one per ``interval`` seconds).
        width: Total width in cells (including the y-axis gutter).
        height: Chart height in cells (excludes the two axis label rows).
        interval: Seconds between samples; with ``window_seconds`` this fixes
            how many samples fill the window.
        window_seconds: The fixed time span of the x-axis.
        unit: Unit suffix for the y-axis labels (e.g. "/s", "%", "s").
        color: Line colour.
        y_max: Optional fixed y-axis ceiling; defaults to max(series) (min 1).
        value_fmt: Optional formatter for the y-axis numbers; defaults to a
            compact numeric format.

    Returns:
        A framed Rich Text chart (empty Text if there is no room to draw).
    """
    gutter = 7
    if width < gutter + 8 or height < 2:
        return Text()

    fmt = value_fmt or (lambda v: f"{v:.0f}" if v >= 10 else f"{v:.1f}")
    chart_w = width - gutter
    dot_cols = chart_w * 2
    dot_rows = height * 4

    # How many samples span the full window; the newest maps to the rightmost
    # dot-column and older samples step left, so the line fills right->left.
    capacity = max(window_seconds // max(interval, 1), 1)
    top = y_max if y_max is not None else (max(series) if series else 1.0)
    if top <= 0:
        top = 1.0

    grid = [[0 for _ in range(chart_w)] for _ in range(height)]

    if series:
        # Keep only what fits the window; map the newest to the right edge.
        visible = series[-capacity:]
        n = len(visible)
        plots: list[tuple[int, int]] = []
        for i, value in enumerate(visible):
            # Age in samples from the newest (0 = now), placed from the right.
            age = (n - 1) - i
            dot_col = (dot_cols - 1) - round(age * (dot_cols - 1) / max(capacity - 1, 1))
            if dot_col < 0:
                continue
            frac = max(0.0, min(1.0, value / top))
            dot_row = int(round((1.0 - frac) * (dot_rows - 1)))
            plots.append((dot_col, dot_row))
        _plot_grid(grid, plots, chart_w, height)

    out = Text()
    n_rows = height
    for i, grid_row in enumerate(grid):
        if i == 0:
            label = f"{fmt(top) + unit:>{gutter - 1}} "
        elif i == n_rows - 1:
            label = f"{fmt(0.0) + unit:>{gutter - 1}} "
        else:
            label = " " * gutter
        out.append(label, style="dim")
        out.append("".join(chr(0x2800 + mask) for mask in grid_row), style=color)
        out.append("\n")

    # X-axis frame + relative time labels (fixed window).
    out.append(" " * gutter + "└" + "─" * (chart_w - 1) + "\n", style="dim")
    left = f"-{_format_ago(window_seconds)}"
    right = "now"
    pad = max(chart_w - len(left) - len(right), 1)
    out.append(" " * gutter + left + " " * pad + right, style="dim")
    return out
