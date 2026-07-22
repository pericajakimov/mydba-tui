"""
Main Textual application for mydba-tui.

This module defines the root TUI application and global application
configuration. Business logic and database operations should remain in
dedicated service modules.
"""

from __future__ import annotations

from functools import partial
from operator import attrgetter
from typing import TYPE_CHECKING

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
    ProfilesScreen,
    SettingsScreen,
    WorkspaceScreen,
)

if TYPE_CHECKING:
    from mydba_tui.cli import CliOptions
    from mydba_tui.models.profile import Profile
    from mydba_tui.ui.screens.password_prompt import Credentials


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
        "profiles": ProfilesScreen,
    }

    def __init__(self, cli_options: CliOptions | None = None) -> None:
        """Initialize the application and load configuration."""
        from mydba_tui.cli import CliOptions

        self.settings: Settings = load_settings()
        self.cli_options: CliOptions = cli_options or CliOptions()
        super().__init__()
        self.theme = self.settings.theme
        self._setup_logging()

    def on_mount(self) -> None:
        """Push the home screen on mount."""
        self.push_screen(HomeScreen())

        # If CLI provided connection params, connect directly
        if self.cli_options.connect_directly:

            self._cli_connect()

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

    def _cli_connect(self) -> None:
        """Handle direct connection from CLI arguments."""

        from mydba_tui.config.profiles import load_profiles

        options = self.cli_options
        profile: Profile | None = None

        if options.profile_name:
            # Look up named profile
            profiles = load_profiles()
            profile = next(
                (p for p in profiles if p.name == options.profile_name), None
            )
            if profile is None:
                self.notify(
                    f"Profile '{options.profile_name}' not found.",
                    severity="error",
                    timeout=10,
                )
                return
        elif options.cli_profile:
            profile = options.cli_profile

        if profile is None:
            return

        # Handle password prompt if -p was given without value
        password = profile.password
        if options.password_prompt and not password:
            # Can't prompt in TUI context — push to profiles screen with creds prompt
            from mydba_tui.ui.screens.password_prompt import (
                CredentialsPromptScreen,
            )

            self.push_screen(
                CredentialsPromptScreen(
                    profile_name=profile.name,
                    host=profile.host,
                    username=profile.username,
                    password="",
                ),
                callback=lambda creds: self._cli_connect_with_creds(profile, creds), 
            )
            return

        # Connect directly via the profiles screen logic
        self._cli_do_connect(profile, password)

    def _cli_connect_with_creds(
        self, profile: Profile, creds: Credentials | None
    ) -> None:
        """Handle credentials from CLI password prompt."""
        if creds is None:
            return
        profile.username = creds.username
        self._cli_do_connect(profile, creds.password)

    def _cli_do_connect(self, profile: Profile, password: str) -> None:
        """Perform the actual connection from CLI mode."""
        from mysql.connector.errors import Error as MySQLError

        from mydba_tui.connection import connect
        from mydba_tui.server import detect
        from mydba_tui.ui.widgets import StatusBar

        if profile.username:
            pass  # already set
        try:
            connection = connect(profile, password)
        except MySQLError as e:
            self.notify(f"Connection failed:\n{e}", severity="error", timeout=10)
            return

        self.db_connection = connection 
        self.active_profile = profile 

        server_info = detect(connection)
        self.server_info = server_info 

        # Build status
        from mydba_tui.ui.screens.profiles import ENVIRONMENT_COLORS, _format_vendor

        env_label = profile.environment.upper()
        env_color = ENVIRONMENT_COLORS.get(profile.environment, "white")
        vendor_display = _format_vendor(server_info)
        role_display = f" | {server_info.role.capitalize()}" if server_info.role else ""
        db_display = f" | {server_info.current_database}" if server_info.current_database else ""
        user_display = f" | {server_info.current_user}" if server_info.current_user else ""

        status = (
            f"[bold {env_color}]{env_label}[/bold {env_color}] {profile.name}"
            f" | {vendor_display}{role_display}{db_display}{user_display}"
        )
        self.connection_status = status 

        # Update status bar on home screen
        try:
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.status_text = status
        except Exception:
            pass


def main() -> None:
    """Application entry point."""
    from mydba_tui.cli import parse_args

    options = parse_args()
    app = MyDBAApp(cli_options=options)
    app.run()


if __name__ == "__main__":
    main()
