"""XML exporter."""

from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape as xml_escape

from mydba_tui.exporters import Exporter


class XmlExporter(Exporter):
    """Export results as XML (similar to mysql --xml output)."""

    name = "XML"
    extension = ".xml"
    format_key = "xml"

    def _write_header(self) -> None:
        assert self._file is not None
        self._file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self._file.write("<resultset>\n")

    def write_row(self, row: tuple[Any, ...] | list[Any]) -> None:
        assert self._file is not None
        self._file.write("  <row>\n")
        for i, val in enumerate(row):
            col = self._col_names[i] if i < len(self._col_names) else f"col{i}"
            if val is None:
                self._file.write(
                    f'    <field name="{xml_escape(col)}" xsi:nil="true" />\n'
                )
            else:
                escaped_val = xml_escape(str(val))
                self._file.write(
                    f'    <field name="{xml_escape(col)}">'
                    f"{escaped_val}</field>\n"
                )
        self._file.write("  </row>\n")
        self._row_count += 1

    def finalize(self) -> None:
        assert self._file is not None
        self._file.write("</resultset>\n")
        super().finalize()
