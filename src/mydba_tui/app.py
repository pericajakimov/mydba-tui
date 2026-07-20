"""
Main Textual application for mydba-tui.

This module defines the root TUI application and global application
configuration. Business logic and database operations should remain in
dedicated service modules.
"""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static

from mydba_tui.config import Settings, load_settings
from mydba_tui.logging import setup_app_logging


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
        self.settings: Settings = load_settings()
        super().__init__()
        self.theme = self.settings.theme
        self._setup_logging()

    def compose(self) -> ComposeResult:
        """Build the initial application layout."""
        yield Header()

        yield Static(
            "Welcome to mydba\n\nDatabase administration starts here.",
            id="main-container",
        )

        yield Footer()

    def _setup_logging(self) -> None:
        """Initialize application logging based on settings."""
        setup_app_logging(level=self.settings.log_level)


def main() -> None:
    """Application entry point."""
    app = MyDBAApp()
    app.run()


if __name__ == "__main__":
    main()
