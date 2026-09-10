"""
Braille line-chart renderer.

Renders a numeric series as a compact line chart using Unicode braille
characters (each cell packs a 2x4 dot grid, giving sub-character resolution).
Produces a Rich Text object suitable for a Static widget — no external
charting dependency. Reused by the Replication lag graph and, later, the
Monitoring page.
"""

from __future__ import annotations

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
