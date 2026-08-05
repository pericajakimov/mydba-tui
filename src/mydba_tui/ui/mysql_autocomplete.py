"""
SQL autocomplete engine for MySQL.

Provides completion suggestions based on:
- MySQL keywords
- MySQL built-in functions
- MySQL data types
- Schema objects (tables, views, columns) from metadata cache
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mydba_tui.ui.mysql_highlight import _FLOW_KEYWORDS, _FUNCTIONS, _KEYWORDS, _TYPES


class CompletionKind(Enum):
    """Type of completion item."""

    KEYWORD = "keyword"
    FUNCTION = "function"
    TYPE = "type"
    TABLE = "table"
    VIEW = "view"
    COLUMN = "column"
    SCHEMA = "schema"
    PROCEDURE = "procedure"


@dataclass(slots=True)
class CompletionItem:
    """A single completion suggestion.

    Attributes:
        text: The text to insert.
        kind: Type of completion.
        detail: Optional additional info (e.g., table name for columns).
    """

    text: str
    kind: CompletionKind
    detail: str = ""

    @property
    def display(self) -> str:
        """Format for display in the completion list."""
        icon = _KIND_ICONS.get(self.kind, " ")
        if self.detail:
            return f"{icon} {self.text}  ({self.detail})"
        return f"{icon} {self.text}"


_KIND_ICONS = {
    CompletionKind.KEYWORD: "⌘",
    CompletionKind.FUNCTION: "ƒ",
    CompletionKind.TYPE: "τ",
    CompletionKind.TABLE: "⊞",
    CompletionKind.VIEW: "⊟",
    CompletionKind.COLUMN: "◇",
    CompletionKind.SCHEMA: "◈",
    CompletionKind.PROCEDURE: "⊕",
}

# Pre-build static completion items
_KEYWORD_ITEMS = [
    CompletionItem(text=kw, kind=CompletionKind.KEYWORD)
    for kw in sorted(_KEYWORDS | _FLOW_KEYWORDS)
]

_FUNCTION_ITEMS = [
    CompletionItem(text=f"{fn}(", kind=CompletionKind.FUNCTION)
    for fn in sorted(_FUNCTIONS)
]

_TYPE_ITEMS = [
    CompletionItem(text=t, kind=CompletionKind.TYPE)
    for t in sorted(_TYPES)
]

# All static items combined
_ALL_STATIC = _KEYWORD_ITEMS + _FUNCTION_ITEMS + _TYPE_ITEMS

# Keywords that can start a SQL statement
_STATEMENT_STARTERS = frozenset({
    "SELECT", "INSERT", "UPDATE", "DELETE", "REPLACE", "MERGE",
    "CREATE", "ALTER", "DROP", "RENAME", "TRUNCATE",
    "SHOW", "DESCRIBE", "DESC", "EXPLAIN", "ANALYZE",
    "USE", "SET", "CALL", "DO",
    "LOCK", "UNLOCK", "FLUSH", "RESET",
    "START", "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT",
    "GRANT", "REVOKE",
    "LOAD", "PREPARE", "EXECUTE", "DEALLOCATE",
    "WITH", "HANDLER",
    "DELIMITER",
})

_STARTER_ITEMS = [
    CompletionItem(text=kw, kind=CompletionKind.KEYWORD)
    for kw in sorted(_STATEMENT_STARTERS)
]


def get_completions(
    prefix: str,
    schema_objects: dict[str, list[str]] | None = None,
    table_columns: dict[str, list[str]] | None = None,
    current_table: str | None = None,
    at_statement_start: bool = False,
) -> list[CompletionItem]:
    """Get completion suggestions for a given prefix.

    Args:
        prefix: The current word being typed (case-insensitive matching).
        schema_objects: Dict mapping category to object names.
            Example: {"tables": ["orders", "users"], "views": ["v_active"]}
        table_columns: Dict mapping table_name to list of column names.
        current_table: Table name in current context (for column suggestions).
        at_statement_start: If True, only suggest keywords (not functions/types).

    Returns:
        List of matching CompletionItems, sorted by relevance.
    """
    if not prefix or len(prefix) < 1:
        return []

    upper_prefix = prefix.upper()
    results: list[CompletionItem] = []

    # Schema objects (skip at statement start — only keywords there)
    if schema_objects and not at_statement_start:
        for category, names in schema_objects.items():
            kind = _CATEGORY_TO_KIND.get(category, CompletionKind.TABLE)
            for name in names:
                if name.upper().startswith(upper_prefix):
                    results.append(CompletionItem(text=name, kind=kind))

    # Columns (if in table context or after dot — skip at statement start)
    if table_columns and current_table and not at_statement_start:
        cols = table_columns.get(current_table, [])
        for col in cols:
            if col.upper().startswith(upper_prefix):
                results.append(CompletionItem(
                    text=col, kind=CompletionKind.COLUMN, detail=current_table
                ))

    # Static items (keywords, functions, types)
    if at_statement_start:
        # Only statement-starting keywords at start
        for item in _STARTER_ITEMS:
            if item.text.upper().startswith(upper_prefix):
                results.append(item)
    else:
        for item in _ALL_STATIC:
            if item.text.upper().startswith(upper_prefix):
                results.append(item)

    # Deduplicate and limit
    seen: set[str] = set()
    unique: list[CompletionItem] = []
    for item in results:
        key = item.text.upper()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique[:50]  # Limit to 50 suggestions


def get_completions_after_dot(
    table_name: str,
    table_columns: dict[str, list[str]] | None = None,
    prefix: str = "",
) -> list[CompletionItem]:
    """Get column completions after a dot (table.column).

    Args:
        table_name: The table/alias before the dot.
        table_columns: Dict mapping table_name to column names.
        prefix: Optional prefix after the dot to filter.

    Returns:
        List of matching column CompletionItems.
    """
    if not table_columns:
        return []

    cols = table_columns.get(table_name, [])
    if not cols:
        # Try case-insensitive match
        for name, columns in table_columns.items():
            if name.upper() == table_name.upper():
                cols = columns
                break

    if not cols:
        return []

    upper_prefix = prefix.upper() if prefix else ""
    results = []
    for col in cols:
        if not upper_prefix or col.upper().startswith(upper_prefix):
            results.append(CompletionItem(
                text=col, kind=CompletionKind.COLUMN, detail=table_name
            ))

    return results[:50]


_CATEGORY_TO_KIND = {
    "tables": CompletionKind.TABLE,
    "views": CompletionKind.VIEW,
    "procedures": CompletionKind.PROCEDURE,
    "functions": CompletionKind.FUNCTION,
    "schemas": CompletionKind.SCHEMA,
}
