"""
Server status bar widget.

Displays the current connection status below the main header.
Shows environment, profile name, server version, role, database, and user.
Supports Rich markup for colored environment labels.
"""

from textual.reactive import reactive
from textual.widget import Widget


class StatusBar(Widget):
    """A status bar showing the current connection information."""

    DEFAULT_CSS = """
    StatusBar {
        width: 100%;
        height: 1;
        background: $surface;
        content-align: center middle;
    }
    """

    status_text: reactive[str] = reactive("[dim]Not connected[/dim]")

    def render(self) -> str:
        """Render the status bar content with Rich markup."""
        return self.status_text
