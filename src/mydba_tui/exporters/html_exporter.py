"""HTML table exporter."""

from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape as xml_escape

from mydba_tui.exporters import Exporter


class HtmlExporter(Exporter):
    """Export results as an HTML table."""

    name = "HTML"
    extension = ".html"
    format_key = "html"

    def _write_header(self) -> None:
        assert self._file is not None
        self._file.write(
            "<!DOCTYPE html>\n<html>\n<head>\n"
            '  <meta charset="UTF-8">\n'
            "  <style>\n"
            "    table { border-collapse: collapse; }\n"
            "    th, td { border: 1px solid #ccc; padding: 4px 8px; "
            "text-align: left; }\n"
            "    th { background: #f0f0f0; }\n"
            "    .null { color: #999; font-style: italic; }\n"
            "  </style>\n"
            "</head>\n<body>\n<table>\n  <thead>\n    <tr>\n"
        )
        for col in self._col_names:
            self._file.write(f"      <th>{xml_escape(col)}</th>\n")
        self._file.write("    </tr>\n  </thead>\n  <tbody>\n")

    def write_row(self, row: tuple[Any, ...] | list[Any]) -> None:
        assert self._file is not None
        self._file.write("    <tr>\n")
        for val in row:
            if val is None:
                self._file.write('      <td class="null">NULL</td>\n')
            else:
                self._file.write(f"      <td>{xml_escape(str(val))}</td>\n")
        self._file.write("    </tr>\n")
        self._row_count += 1

    def finalize(self) -> None:
        assert self._file is not None
        self._file.write("  </tbody>\n</table>\n</body>\n</html>\n")
        super().finalize()
