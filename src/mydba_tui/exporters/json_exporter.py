"""JSON and JSONL exporters."""

from __future__ import annotations

import json
from typing import Any

from mydba_tui.exporters import Exporter
from mydba_tui.exporters.utils import json_value


class JsonlExporter(Exporter):
    """Export results as JSONL (one JSON object per line)."""

    name = "JSONL"
    extension = ".jsonl"
    format_key = "jsonl"

    def _write_header(self) -> None:
        pass

    def write_row(self, row: tuple[Any, ...] | list[Any]) -> None:
        assert self._file is not None
        obj = {}
        for i, val in enumerate(row):
            col = self._col_names[i] if i < len(self._col_names) else f"col{i}"
            obj[col] = json_value(val)
        self._file.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
        self._row_count += 1


class JsonExporter(Exporter):
    """Export results as a single JSON array of objects."""

    name = "JSON"
    extension = ".json"
    format_key = "json"

    def __init__(self) -> None:
        super().__init__()
        self._rows_data: list[dict[str, Any]] = []

    def _write_header(self) -> None:
        pass

    def write_row(self, row: tuple[Any, ...] | list[Any]) -> None:
        obj = {}
        for i, val in enumerate(row):
            col = self._col_names[i] if i < len(self._col_names) else f"col{i}"
            obj[col] = json_value(val)
        self._rows_data.append(obj)
        self._row_count += 1

    def finalize(self) -> None:
        assert self._file is not None
        json.dump(
            self._rows_data,
            self._file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        self._file.write("\n")
        super().finalize()
