"""
Main Textual application for mydba-tui.

This module defines the root TUI application and global application
configuration. Business logic and database operations should remain in
dedicated service modules.
"""

from functools import partial
from operator import attrgetter

from rich.text import Text
from textual.app import App, ComposeResult
from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.widgets import Footer, Header

from mydba_tui.config import Settings, load_settings, save_settings
from mydba_tui.logging import setup_app_logging
from mydba_tui.ui.screens import (
    AdministrationScreen,
    BrowserScreen,
    HomeScreen,
    MonitoringScreen,
    SettingsScreen,
    WorkspaceScreen,
)


class MyDBAThemeProvider(Provider):
    """Theme provider that marks the currently active theme."""

    @property
    def commands(self) -> list[tuple[Text, str, partial[None]]]:
        """Build theme command list with active indicator."""
        themes = self.app.available_themes
        current = self.app.theme

        def set_app_theme(name: str) -> None:
            self.app.theme = name

        result: list[tuple[Text, str, partial[None]]] = []
        for theme in sorted(themes.values(), key=attrgetter("name")):
            if theme.name == current:
                display = Text.assemble(("● ", "bold green"), theme.name)
            else:
                display = Text.assemble(("  ", ""), theme.name)
            result.append((display, theme.name, partial(set_app_theme, theme.name)))
        return result

    async def discover(self) -> Hits:
        """Yield all themes for discovery."""
        for display, _name, callback in self.commands:
            yield DiscoveryHit(display, callback)

    async def search(self, query: str) -> Hits:
        """Search themes by name."""
        matcher = self.matcher(query)
        for display, name, callback in self.commands:
            if (match := matcher.match(name)) > 0:
                yield Hit(match, display, callback)


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

    #home-menu {
        height: 1fr;
        padding: 1 2;
    }
    """

    SCREENS = {
        "browser": BrowserScreen,
        "workspace": WorkspaceScreen,
        "administration": AdministrationScreen,
        "monitoring": MonitoringScreen,
        "settings": SettingsScreen,
    }

    def __init__(self) -> None:
        """Initialize the application and load configuration."""
        self.settings: Settings = load_settings()
        super().__init__()
        self.theme = self.settings.theme
        self._setup_logging()

    def on_mount(self) -> None:
        """Push the home screen on mount."""
        self.push_screen(HomeScreen())

    def watch_theme(self, theme: str) -> None:
        """Persist theme selection when the user changes it."""
        if theme != self.settings.theme:
            self.settings.theme = theme
            save_settings(self.settings)

    def search_themes(self) -> None:
        """Show theme picker with active theme indicator."""
        from textual.command import CommandPalette

        self.push_screen(
            CommandPalette(
                providers=[MyDBAThemeProvider],
                placeholder="Search for themes…",
            ),
        )

    def compose(self) -> ComposeResult:
        """Build the default screen layout (used before home screen mounts)."""
        yield Header()
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
