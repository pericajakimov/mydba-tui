"""
Shared table cell rendering helpers.

Provides type-aware cell formatting and coloring used to present database
values consistently across the SQL Workspace results and the Administration
lists. Cell values are colored by their Python type, and JSON strings are
syntax-highlighted.
"""

import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from rich.style import Style
from rich.text import Text

# --- Cell coloring palette ---

S_NULL = Style(color="#666666", italic=True)  # Gray — NULL
S_NUMBER = Style(color="#b5cea8")  # Light green — integers
S_DECIMAL = Style(color="#d7ba7d")  # Warm gold — decimals/floats
S_STRING = Style(color="#ce9178")  # Orange — strings (same as SQL editor)
S_DATE = Style(color="#4ec9b0")  # Teal — dates/times
S_BINARY = Style(color="#c586c0")  # Purple — binary/hex
S_BORDER = Style(color="#555555")  # Dark gray — table borders
S_HEADER = Style(bold=True)  # Bold — column headers
S_JSON_KEY = Style(color="#569cd6")  # Blue — JSON keys
S_JSON_STRING = Style(color="#ce9178")  # Orange — JSON strings
S_JSON_NUMBER = Style(color="#b5cea8")  # Light green — JSON numbers
S_JSON_BOOL = Style(color="#7daf9c")  # Muted teal — JSON booleans/null
S_JSON_BRACE = Style(color="#cccccc")  # Light gray — braces/brackets


def format_cell(val: Any) -> str:
    """Format a cell value for display.

    - Binary → always hex
    - Text → full content (no truncation)
    - NULL → literal "NULL" string
    """
    if val is None:
        return "NULL"
    if isinstance(val, (bytes, bytearray)):
        return "0x" + val.hex().upper()
    return str(val)


def looks_like_datetime(s: str) -> bool:
    """Quick check if a string looks like a date/datetime."""
    if len(s) >= 10 and s[4:5] == "-" and s[7:8] == "-":
        return True  # YYYY-MM-DD...
    if len(s) == 8 and s[2:3] == ":" and s[5:6] == ":":
        return True  # HH:MM:SS
    return False


def cell_style(val: Any) -> Style:
    """Determine the display style for a cell value based on its Python type."""
    if val is None:
        return S_NULL
    if isinstance(val, (bytes, bytearray)):
        return S_BINARY
    if isinstance(val, int):
        return S_NUMBER
    if isinstance(val, (float, Decimal)):
        return S_DECIMAL
    if isinstance(val, (datetime, date, time, timedelta)):
        return S_DATE
    s = str(val)
    if looks_like_datetime(s):
        return S_DATE
    return S_STRING


def is_json(s: str) -> bool:
    """Quick check if a string looks like JSON."""
    stripped = s.strip()
    if not stripped:
        return False
    if (stripped[0] == "{" and stripped[-1] == "}") or (stripped[0] == "[" and stripped[-1] == "]"):
        import json

        try:
            json.loads(stripped)
            return True
        except (json.JSONDecodeError, ValueError):
            return False
    return False


_JSON_TOKEN_RE = re.compile(
    r"""
    (?P<string>"(?:[^"\\]|\\.)*")  |
    (?P<number>-?\d+\.?\d*(?:[eE][+-]?\d+)?)  |
    (?P<bool>true|false|null)  |
    (?P<brace>[{}\[\]])  |
    (?P<punct>[,:])  |
    (?P<ws>\s+)  |
    (?P<other>.)
    """,
    re.VERBOSE,
)


def highlight_json(s: str) -> Text:
    """Highlight a JSON string with colors."""
    text = Text()
    tokens = list(_JSON_TOKEN_RE.finditer(s))
    for idx, match in enumerate(tokens):
        token = match.group()
        kind = match.lastgroup

        if kind == "string":
            # Check if this string is a key (followed by :)
            is_key = False
            for lookahead in tokens[idx + 1 :]:
                if lookahead.lastgroup == "ws":
                    continue
                if lookahead.group() == ":":
                    is_key = True
                break
            if is_key:
                text.append(token, style=S_JSON_KEY)
            else:
                text.append(token, style=S_JSON_STRING)
        elif kind == "number":
            text.append(token, style=S_JSON_NUMBER)
        elif kind == "bool":
            text.append(token, style=S_JSON_BOOL)
        elif kind == "brace":
            text.append(token, style=S_JSON_BRACE)
        elif kind == "punct":
            text.append(token, style=S_JSON_BRACE)
        else:
            text.append(token)
    return text


def styled_cell(val: Any) -> Text:
    """Create a styled Text for a single cell value."""
    s = format_cell(val)
    style = cell_style(val)

    # If it's a string value and looks like JSON, highlight it
    if style == S_STRING and isinstance(val, str) and is_json(val):
        return highlight_json(val)

    t = Text(s)
    t.stylize(style)
    return t


# --- Lock mode / type explanations ---

# InnoDB row-lock mode components (from performance_schema data_locks /
# sys.innodb_lock_waits). A mode is a comma-separated combination, e.g.
# "X,REC_NOT_GAP" or "S,GAP".
_INNODB_LOCK_COMPONENTS = {
    "X": "Exclusive",
    "S": "Shared",
    "IX": "Intention Exclusive",
    "IS": "Intention Shared",
    "GAP": "gap lock",
    "REC_NOT_GAP": "record only (no gap)",
    "INSERT_INTENTION": "insert intention",
    "AUTO_INC": "auto-increment",
    "UNKNOWN": "unknown",
}

# Metadata (table) lock types from the MDL subsystem.
_MDL_LOCK_TYPES = {
    "INTENTION_EXCLUSIVE": "Intention Exclusive",
    "SHARED": "Shared",
    "SHARED_HIGH_PRIO": "Shared (high priority)",
    "SHARED_READ": "Shared Read",
    "SHARED_WRITE": "Shared Write",
    "SHARED_UPGRADABLE": "Shared Upgradable",
    "SHARED_NO_WRITE": "Shared, No Write",
    "SHARED_NO_READ_WRITE": "Shared, No Read/Write",
    "EXCLUSIVE": "Exclusive",
}


def explain_lock_mode(mode: str) -> str:
    """Return a human-readable explanation of a lock mode/type, or "" if empty.

    Handles InnoDB row-lock modes (comma-separated components such as
    "X,REC_NOT_GAP") and MDL lock types (single words such as "SHARED_READ").
    Unknown tokens are passed through unchanged so nothing is hidden.
    """
    mode = (mode or "").strip()
    if not mode:
        return ""

    # MDL single-word type.
    if mode in _MDL_LOCK_TYPES:
        return _MDL_LOCK_TYPES[mode]

    # InnoDB comma-separated components.
    parts = [p.strip() for p in mode.split(",") if p.strip()]
    explained = [_INNODB_LOCK_COMPONENTS.get(p, p) for p in parts]
    return ", ".join(explained)
