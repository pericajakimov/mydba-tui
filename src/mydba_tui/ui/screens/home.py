"""
Home screen.

Landing page displayed before a database connection is established.
Prompts the user to connect.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from mydba_tui.ui.widgets import StatusBar


class HomeScreen(Screen[None]):
    """Home screen — shown before connecting."""

    BINDINGS = [
        Binding("c", "open_profiles", "Connections", key_display="C"),
        Binding("f10", "quit", "Exit", key_display="F10"),
    ]

    def compose(self) -> ComposeResult:
        """Build the home screen layout."""
        yield Header()
        yield StatusBar(id="status-bar")

        yield Static(
            "[b]mydba[/b] — MySQL Database Administration Tool\n"
            "\n"
            "  Press [bold]c[/bold] to open Connection Profiles\n"
            "\n"
            "  [bold]F10[/bold] Exit",
            id="home-menu",
        )

        yield Footer()

    def on_screen_resume(self) -> None:
        """Update status bar when returning to this screen."""
        status = getattr(self.app, "connection_status", "")
        if status:
            self.query_one("#status-bar", StatusBar).status_text = status

    def action_open_profiles(self) -> None:
        """Navigate to the Connection Profiles screen."""
        self.app.push_screen("profiles")

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()
