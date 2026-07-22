"""
Object Browser screen.

Placeholder for the database object browser module.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class BrowserScreen(Screen[None]):
    """Object Browser — browse database schemas and objects."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", key_display="Esc"),
    ]

    def compose(self) -> ComposeResult:
        """Build the browser screen layout."""
        yield Header()
        yield Static(
            "[b]Object Browser[/b]\n\n  [dim]Connect to a database to browse objects.[/dim]",
            id="browser-content",
        )
        yield Footer()
