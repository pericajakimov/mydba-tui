"""Markdown table exporter."""

from __future__ import annotations

from typing import Any

from mydba_tui.exporters import Exporter


class MarkdownExporter(Exporter):
    """Export results as a Markdown table."""

    name = "Markdown"
    extension = ".md"
    format_key = "markdown"

    def _write_header(self) -> None:
        assert self._file is not None
        header = "| " + " | ".join(self._col_names) + " |"
        separator = "| " + " | ".join("---" for _ in self._col_names) + " |"
        self._file.write(header + "\n")
        self._file.write(separator + "\n")

    def write_row(self, row: tuple[Any, ...] | list[Any]) -> None:
        assert self._file is not None
        cells = []
        for val in row:
            if val is None:
                cells.append("NULL")
            elif isinstance(val, (bytes, bytearray)):
                cells.append("0x" + val.hex().upper())
            else:
                # Escape pipe characters in markdown
                cells.append(str(val).replace("|", "\\|"))
        line = "| " + " | ".join(cells) + " |"
        self._file.write(line + "\n")
        self._row_count += 1
