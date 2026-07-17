"""
Server information screen.

Displays MySQL server information, capabilities, configuration details,
and operational metadata.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class ServerScreen(Screen[None]):
    """
    MySQL server overview screen.

    Future functionality:
    - server version detection
    - engine information
    - configuration variables
    - status counters
    - replication information
    - Aurora-specific information when detected
    """

    def compose(self) -> ComposeResult:
        """
        Compose the server screen layout.
        """
        yield Static(
            "Server Information\n\nServer details will be displayed here.",
            id="server-screen-content",
        )
