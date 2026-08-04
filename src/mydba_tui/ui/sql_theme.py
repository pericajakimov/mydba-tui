"""
Custom SQL theme for TextArea widgets.

Extends vscode_dark with additional highlight group mappings
for SQL-specific node types (attributes, storage classes, qualifiers, fields).
"""

from __future__ import annotations

from rich.style import Style
from textual.widgets._text_area import TextAreaTheme  # type: ignore[attr-defined]

# Name used to register and reference this theme
SQL_THEME_NAME = "mydba"

# Build custom theme extending vscode_dark
_base = TextAreaTheme.get_builtin_theme("vscode_dark")
assert _base is not None

SQL_THEME = TextAreaTheme(
    name=SQL_THEME_NAME,
    base_style=_base.base_style,
    cursor_style=_base.cursor_style,
    cursor_line_style=_base.cursor_line_style,
    bracket_matching_style=_base.bracket_matching_style,
    cursor_line_gutter_style=_base.cursor_line_gutter_style,
    selection_style=_base.selection_style,
    gutter_style=_base.gutter_style,
    syntax_styles={
        **_base.syntax_styles,
        # SQL-specific additions for unmapped highlight groups
        "attribute": Style(color="#9cdcfe"),
        "storageclass": Style(color="#569cd6"),
        "type.qualifier": Style(color="#4ec9b0"),
        "field": Style(color="#9cdcfe"),
        "variable": Style(color="#9cdcfe"),
        "parameter": Style(color="#9cdcfe"),
    },
)
