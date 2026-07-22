"""
Monitoring screen.

Placeholder for the lightweight server monitoring module.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class MonitoringScreen(Screen[None]):
    """Monitoring — lightweight live server monitoring."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", key_display="Esc"),
    ]

    def compose(self) -> ComposeResult:
        """Build the monitoring screen layout."""
        yield Header()
        yield Static(
            "[b]Monitoring[/b]\n\n  [dim]Connect to a database to view live metrics.[/dim]",
            id="monitoring-content",
        )
        yield Footer()
