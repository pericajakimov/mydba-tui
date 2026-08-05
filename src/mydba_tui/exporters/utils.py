"""Shared utility functions for exporters.

Value formatting helpers used across multiple exporter implementations.
"""

from __future__ import annotations

from typing import Any


def format_delimited_value(val: Any) -> str:
    """Format a value for CSV/TSV export (MySQL compatible).

    NULL → \\N (MySQL LOAD DATA convention)
    Special chars escaped per MySQL escape sequences (Table 11.1).
    """
    if val is None:
        return "\\N"
    if isinstance(val, (bytes, bytearray)):
        return "0x" + val.hex().upper()
    s = str(val)
    # Escape special characters (MySQL Table 11.1)
    s = s.replace("\\", "\\\\")
    s = s.replace("\x00", "\\0")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")
    s = s.replace("\x1a", "\\Z")  # Ctrl+Z (Windows EOF)
    return s


def sql_value(val: Any) -> str:
    """Format a value for SQL INSERT statement."""
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (bytes, bytearray)):
        return "X'" + val.hex().upper() + "'"
    # String — escape single quotes and backslashes
    s = str(val).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


def json_value(val: Any) -> Any:
    """Convert a value for JSON serialization."""
    if val is None:
        return None
    if isinstance(val, (bytes, bytearray)):
        return "0x" + val.hex().upper()
    if isinstance(val, (int, float)):
        return val
    return str(val)
