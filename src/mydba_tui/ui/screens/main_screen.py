"""
Main application screen.

Provides the primary workspace view displayed after starting mydba-tui.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class MainScreen(Screen[None]):
    """
    Default application screen.

    This screen will later become the main DBA workspace containing:
    - database connection status
    - object browser
    - SQL editor
    - metadata panels
    - operational views
    """

    def compose(self) -> ComposeResult:
        """
        Compose the main screen layout.
        """
        yield Static(
            "mydba workspace\n\nUse the navigation menu to explore database objects.",
            id="main-screen-content",
        )
