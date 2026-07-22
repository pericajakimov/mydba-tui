"""
Home screen.

The main navigation screen displayed after application startup.
Provides access to all application modules.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from mydba_tui.ui.widgets import StatusBar


class HomeScreen(Screen[None]):
    """Home screen with module navigation menu."""

    BINDINGS = [
        Binding("f1", "open_browser", "Browser"),
        Binding("f2", "open_workspace", "SQL"),
        Binding("f3", "open_admin", "Admin"),
        Binding("f4", "open_monitoring", "Monitor"),
        Binding("f5", "open_settings", "Settings"),
        Binding("c", "open_profiles", "Connections"),
        Binding("f10", "quit", "Exit"),
    ]

    def compose(self) -> ComposeResult:
        """Build the home screen layout."""
        yield Header()
        yield StatusBar(id="status-bar")

        yield Static(
            "[b]mydba[/b] — MySQL Database Administration Tool\n"
            "\n"
            "  [bold]F1[/bold]  Object Browser\n"
            "  [bold]F2[/bold]  SQL Workspace\n"
            "  [bold]F3[/bold]  Administration\n"
            "  [bold]F4[/bold]  Monitoring\n"
            "  [bold]F5[/bold]  Settings\n"
            "  [bold]c[/bold]   Connections\n"
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

    def action_open_browser(self) -> None:
        """Navigate to the Object Browser."""
        self.app.push_screen("browser")

    def action_open_workspace(self) -> None:
        """Navigate to the SQL Workspace."""
        self.app.push_screen("workspace")

    def action_open_admin(self) -> None:
        """Navigate to the Administration screen."""
        self.app.push_screen("administration")

    def action_open_monitoring(self) -> None:
        """Navigate to the Monitoring screen."""
        self.app.push_screen("monitoring")

    def action_open_settings(self) -> None:
        """Navigate to the Settings screen."""
        self.app.push_screen("settings")

    def action_open_profiles(self) -> None:
        """Navigate to the Connection Profiles screen."""
        self.app.push_screen("profiles")

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()
