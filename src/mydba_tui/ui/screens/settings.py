"""
Settings screen.

Placeholder for the application settings module.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class SettingsScreen(Screen[None]):
    """Settings — application configuration."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Build the settings screen layout."""
        yield Header()
        yield Static(
            "[b]Settings[/b]\n\n  [dim]Application settings will be available here.[/dim]",
            id="settings-content",
        )
        yield Footer()
