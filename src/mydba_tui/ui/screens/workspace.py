"""
SQL Workspace screen.

Placeholder for the integrated SQL editor module.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class WorkspaceScreen(Screen[None]):
    """SQL Workspace — interactive SQL editor and results viewer."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Build the workspace screen layout."""
        yield Header()
        yield Static(
            "[b]SQL Workspace[/b]\n\n"
            "  [dim]Connect to a database to execute SQL.[/dim]",
            id="workspace-content",
        )
        yield Footer()
