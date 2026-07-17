"""
Connection screen.

Provides database connection profile selection and authentication workflow.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class ConnectScreen(Screen[None]):
    """
    Database connection screen.

    Future functionality:
    - list stored connection profiles
    - create and edit profiles
    - request credentials
    - connect to MySQL servers
    - validate server capabilities
    - display connection errors
    """

    def compose(self) -> ComposeResult:
        """
        Compose the connection screen layout.
        """
        yield Static(
            "Connect to Database\n\nConnection profiles will be displayed here.",
            id="connect-screen-content",
        )
