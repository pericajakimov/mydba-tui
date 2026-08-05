"""
Exporters package.

Provides a pluggable export framework for query results.
Each exporter is a separate module in this directory.

Exporters are auto-discovered: any module in this package that defines
a class inheriting from `Exporter` is automatically registered.

To add a new exporter:
1. Create a new .py file in this directory
2. Define a class that inherits from Exporter
3. Set the class attributes: name, extension, format_key
4. Implement _write_header(), write_row(), and optionally finalize()

The exporter will be automatically available in the export format dialog.
"""

from __future__ import annotations

import importlib
import pkgutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TextIO


class Exporter(ABC):
    """Base class for result set exporters.

    Subclasses must define:
        name: Human-readable format name (shown in UI)
        extension: File extension (e.g. ".csv")
        format_key: Unique key for registry (e.g. "csv")
    """

    name: str = ""
    extension: str = ""
    format_key: str = ""

    def __init__(self) -> None:
        self._file: TextIO | None = None
        self._col_names: list[str] = []
        self._row_count: int = 0

    def initialize(self, file: TextIO, col_names: list[str]) -> None:
        """Initialize the exporter with the output file and column names."""
        self._file = file
        self._col_names = col_names
        self._row_count = 0
        self._write_header()

    @abstractmethod
    def _write_header(self) -> None:
        """Write format-specific header (if any)."""

    @abstractmethod
    def write_row(self, row: tuple[Any, ...] | list[Any]) -> None:
        """Write a single data row."""

    def finalize(self) -> None:
        """Finalize the export (write footer if needed, flush)."""
        if self._file:
            self._file.flush()

    @property
    def row_count(self) -> int:
        return self._row_count


def export_result_set(
    col_names: list[str],
    rows: list[Any],
    path: Path,
    exporter: Exporter,
) -> int:
    """Export a result set to a file using the given exporter.

    Args:
        col_names: Column names.
        rows: Result rows.
        path: Destination file path.
        exporter: Exporter instance to use.

    Returns:
        Number of rows written.

    Raises:
        FileExistsError: If the file already exists.
    """
    if path.exists():
        raise FileExistsError(f"File already exists: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        exporter.initialize(f, col_names)
        for row in rows:
            exporter.write_row(row)
        exporter.finalize()

    return exporter.row_count


# --- Auto-discovery ---

EXPORTERS: dict[str, type[Exporter]] = {}
"""Registry of available exporters, keyed by format_key."""


def _discover_exporters() -> None:
    """Auto-discover all Exporter subclasses in this package."""
    package_dir = Path(__file__).parent

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f".{module_info.name}", __package__)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Exporter)
                and attr is not Exporter
                and attr.format_key
            ):
                EXPORTERS[attr.format_key] = attr


_discover_exporters()
