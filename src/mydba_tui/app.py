"""
Main Textual application for mydba-tui.

This module defines the root TUI application and global application
configuration. Business logic and database operations should remain in
dedicated service modules.
"""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static

from mydba_tui.config import Settings, load_settings


class MyDBAApp(App[None]):
    """
    Main mydba terminal application.

    The application shell is intentionally lightweight. Future features
    should be implemented as screens, views, services, and plugins.
    """

    TITLE = "mydba"
    SUB_TITLE = "MySQL Database Administration Tool"

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        height: 1fr;
        padding: 1;
    }
    """

    def __init__(self) -> None:
        """Initialize the application and load configuration."""
        super().__init__()
        self.settings: Settings = load_settings()

    def compose(self) -> ComposeResult:
        """Build the initial application layout."""
        yield Header()

        yield Static(
            "Welcome to mydba\n\nDatabase administration starts here.",
            id="main-container",
        )

        yield Footer()


def main() -> None:
    """Application entry point."""
    app = MyDBAApp()
    app.run()


if __name__ == "__main__":
    main()
