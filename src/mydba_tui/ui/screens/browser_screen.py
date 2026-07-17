"""
Database browser screen.

Provides navigation through MySQL metadata objects such as databases,
tables, indexes, partitions, views, and stored routines.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class BrowserScreen(Screen[None]):
    """
    Metadata-first database browser screen.

    The browser intentionally focuses on database structure and metadata
    instead of automatically displaying table data.
    """

    def compose(self) -> ComposeResult:
        """
        Compose the browser screen layout.
        """
        yield Static(
            "Database Browser\n\n"
            "Schemas\n"
            " └── Tables\n"
            " └── Views\n"
            " └── Indexes\n"
            " └── Partitions\n"
            " └── Routines\n",
            id="browser-screen-content",
        )
