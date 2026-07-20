"""
Administration screen.

Placeholder for the server administration module.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class AdministrationScreen(Screen[None]):
    """Administration — server operational information."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Build the administration screen layout."""
        yield Header()
        yield Static(
            "[b]Administration[/b]\n\n"
            "  [dim]Connect to a database to view server information.[/dim]",
            id="admin-content",
        )
        yield Footer()
