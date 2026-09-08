"""CSV and CSV-semicolon exporters."""

from __future__ import annotations

import csv
from typing import Any

from mydba_tui.exporters import Exporter
from mydba_tui.exporters.utils import format_delimited_value


class CsvExporter(Exporter):
    """Export results as CSV (comma-separated, UTF-8, \\N for NULL)."""

    name = "CSV"
    extension = ".csv"
    format_key = "csv"

    def __init__(self) -> None:
        super().__init__()
        self._writer: Any = None

    def _write_header(self) -> None:
        assert self._file is not None
        self._writer = csv.writer(self._file, quoting=csv.QUOTE_MINIMAL)
        self._writer.writerow(self._col_names)

    def write_row(self, row: tuple[Any, ...] | list[Any]) -> None:
        assert self._writer is not None
        formatted = [format_delimited_value(v) for v in row]
        self._writer.writerow(formatted)
        self._row_count += 1


class CsvSemicolonExporter(Exporter):
    """Export results as CSV with semicolon delimiter (common in Europe)."""

    name = "CSV (;)"
    extension = ".csv"
    format_key = "csv_semicolon"

    def __init__(self) -> None:
        super().__init__()
        self._writer: Any = None

    def _write_header(self) -> None:
        assert self._file is not None
        self._writer = csv.writer(self._file, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        self._writer.writerow(self._col_names)

    def write_row(self, row: tuple[Any, ...] | list[Any]) -> None:
        assert self._writer is not None
        formatted = [format_delimited_value(v) for v in row]
        self._writer.writerow(formatted)
        self._row_count += 1
