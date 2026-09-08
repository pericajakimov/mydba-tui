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
from textual import work
from textual.app import App, ComposeResult
from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.widgets import Footer, Header

from mydba_tui.config import Settings, load_settings, save_settings
from mydba_tui.logging import setup_app_logging
from mydba_tui.ui.screens import (
    AdministrationScreen,
    BrowserScreen,
    MonitoringScreen,
    ProfilesScreen,
    SettingsScreen,
    WorkspaceScreen,
)
from mydba_tui.ui.screens.main_workspace import MainWorkspaceScreen

if TYPE_CHECKING:
    from mydba_tui.cli import CliOptions
    from mydba_tui.connection import ConnectionResult
    from mydba_tui.models.profile import Profile
    from mydba_tui.server import ServerInfo
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
        # Shared connection state (set on connect / reconnect).
        self.db_connection: ConnectionResult | None = None
        self.active_profile: Profile | None = None
        self.server_info: ServerInfo | None = None
        self.connection_status: str = ""
        super().__init__()
        self.theme = self.settings.theme
        self._setup_logging()

    def on_mount(self) -> None:
        """Push the main workspace and open profiles if not connected."""
        self.push_screen(MainWorkspaceScreen())

        # If CLI provided connection params, connect directly
        if self.cli_options.connect_directly:
            self._cli_connect()
        else:
            # No connection yet — open profiles modal
            self.push_screen("profiles")

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
            profile = next((p for p in profiles if p.name == options.profile_name), None)
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

    def _cli_connect_with_creds(self, profile: Profile, creds: Credentials | None) -> None:
        """Handle credentials from CLI password prompt."""
        if creds is None:
            return
        profile.username = creds.username
        self._cli_do_connect(profile, creds.password)

    def _cli_do_connect(self, profile: Profile, password: str) -> None:
        """Perform the actual connection from CLI mode."""
        from mydba_tui.connection import connect

        try:
            result = connect(profile, password)
        except Exception as e:
            self.notify(f"Connection failed:\n{e}", severity="error", timeout=10)
            return

        self.apply_connection(profile, result)

        # Switch to main workspace
        self.pop_screen()  # Pop profiles if it's on top

    # --- Connection state management ---

    @staticmethod
    def _same_endpoint(a: Profile | None, b: Profile | None) -> bool:
        """Return True if two profiles target the same connection endpoint.

        Endpoint identity is (host, port, username). Reconnecting to the same
        endpoint is treated as a fresh MySQL session for the same logical work
        session, so the session log and editor contents are preserved.
        Switching endpoints rotates the session log and clears the workspace.
        """
        if a is None or b is None:
            return False
        return (a.host, a.port, a.username) == (b.host, b.port, b.username)

    def apply_connection(self, profile: Profile, conn_result: ConnectionResult) -> None:
        """Apply a freshly established connection as the active connection.

        Closes any existing connection (and its SSH tunnel) to avoid leaks,
        updates all shared app state, and rebuilds the status string. If the
        new profile targets a different endpoint than the previous one, the
        SQL workspace session log is rotated and its editor/results cleared.

        Args:
            profile: The connected profile.
            conn_result: The live connection result to adopt.
        """
        from mydba_tui.server import detect
        from mydba_tui.ui.screens.profiles import build_connection_status

        previous_profile: Profile | None = getattr(self, "active_profile", None)
        # First connect (no previous profile) is not a "change" — there is
        # nothing to rotate or clear. Only an actual switch between two
        # different endpoints should reset the workspace.
        is_first_connect = previous_profile is None
        endpoint_changed = not is_first_connect and not self._same_endpoint(
            previous_profile, profile
        )

        # Close the previous connection/tunnel before replacing it.
        previous = getattr(self, "db_connection", None)
        if previous is not None and previous is not conn_result:
            try:
                previous.close()
            except Exception:
                pass

        self.db_connection = conn_result
        self.active_profile = profile

        server_info = detect(conn_result.connection)
        self.server_info = server_info
        self.connection_status = build_connection_status(profile, server_info)

        # Any new connection invalidates cached metadata used by autocomplete,
        # since the server catalog may differ (fresh session or new endpoint).
        self._invalidate_metadata_caches()

        # Rotate the SQL workspace session log only when the endpoint changed.
        if endpoint_changed:
            self._reset_workspace_for_new_connection()

    def _invalidate_metadata_caches(self) -> None:
        """Clear cached schema/object/column metadata used by autocomplete."""
        for attr in (
            "_autocomplete_cache",
            "_autocomplete_current_db",
            "_column_cache",
            "_schema_objects_map",
        ):
            if hasattr(self, attr):
                setattr(self, attr, None)

    def disconnect(self) -> None:
        """Close and clear the active connection, if any."""
        previous = getattr(self, "db_connection", None)
        if previous is not None:
            try:
                previous.close()
            except Exception:
                pass
        self.db_connection = None

    def _reset_workspace_for_new_connection(self) -> None:
        """Clear the SQL workspace state when switching connection endpoints."""
        try:
            workspace = self.get_screen("workspace", WorkspaceScreen)
        except Exception:
            return
        workspace.reset_for_new_connection()

    def reconnect(self) -> None:
        """Reconnect to the current profile, refreshing the session context.

        Tears down the existing connection and re-establishes it using the
        active profile. Because the endpoint is unchanged, the session log and
        editor contents are preserved while all metadata (schema tree, object
        browser) reloads on resume. If there is no active profile, opens the
        profiles screen instead.
        """
        profile: Profile | None = getattr(self, "active_profile", None)
        if profile is None:
            self.push_screen("profiles")
            return
        self.notify(f"Reconnecting to {profile.name} ...", severity="information")
        self._reconnect_worker(profile)

    @work(thread=True)
    def _reconnect_worker(self, profile: Profile) -> None:
        """Background worker that re-establishes the connection."""
        from mydba_tui.connection import connect

        password = profile.password
        try:
            result = connect(profile, password)
        except Exception as e:
            self.call_from_thread(
                self.notify, f"Reconnect failed:\n{e}", severity="error", timeout=10
            )
            return
        self.call_from_thread(self._on_reconnect_success, profile, result)

    def _on_reconnect_success(self, profile: Profile, result: ConnectionResult) -> None:
        """Adopt the reconnected session and refresh visible screens."""
        self.apply_connection(profile, result)
        self.notify(f"Reconnected to {profile.name}", severity="information")
        # Refresh whichever screen is on top (browser tree / workspace status).
        screen = self.screen
        for hook in ("reload_after_reconnect", "on_screen_resume"):
            method = getattr(screen, hook, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass
                break


def main() -> None:
    """Application entry point."""
    from mydba_tui.cli import parse_args

    options = parse_args()
    app = MyDBAApp(cli_options=options)
    app.run()


if __name__ == "__main__":
    main()
