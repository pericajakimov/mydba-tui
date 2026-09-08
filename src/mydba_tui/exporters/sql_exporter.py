"""SQL INSERT exporters."""

from __future__ import annotations

from typing import Any

from mydba_tui.exporters import Exporter
from mydba_tui.exporters.utils import sql_value


class SqlInsertExporter(Exporter):
    """Export results as individual SQL INSERT statements."""

    name = "SQL INSERT"
    extension = ".sql"
    format_key = "sql"

    def __init__(self, table_name: str = "exported_data") -> None:
        super().__init__()
        self._table_name = table_name

    def _write_header(self) -> None:
        pass

    def write_row(self, row: tuple[Any, ...] | list[Any]) -> None:
        assert self._file is not None
        values = ", ".join(sql_value(v) for v in row)
        cols = ", ".join(f"`{c}`" for c in self._col_names)
        self._file.write(f"INSERT INTO `{self._table_name}` ({cols}) VALUES ({values});\n")
        self._row_count += 1


class SqlInsertBatchExporter(Exporter):
    """Export results as batched multi-row INSERT statements (100 per batch)."""

    name = "SQL INSERT (batch)"
    extension = ".sql"
    format_key = "sql_batch"
    BATCH_SIZE = 100

    def __init__(self, table_name: str = "exported_data") -> None:
        super().__init__()
        self._table_name = table_name
        self._batch: list[str] = []

    def _write_header(self) -> None:
        pass

    def write_row(self, row: tuple[Any, ...] | list[Any]) -> None:
        values = "(" + ", ".join(sql_value(v) for v in row) + ")"
        self._batch.append(values)
        self._row_count += 1
        if len(self._batch) >= self.BATCH_SIZE:
            self._flush_batch()

    def finalize(self) -> None:
        if self._batch:
            self._flush_batch()
        super().finalize()

    def _flush_batch(self) -> None:
        assert self._file is not None
        if not self._batch:
            return
        cols = ", ".join(f"`{c}`" for c in self._col_names)
        values_str = ",\n  ".join(self._batch)
        self._file.write(f"INSERT INTO `{self._table_name}` ({cols}) VALUES\n  {values_str};\n\n")
        self._batch.clear()
