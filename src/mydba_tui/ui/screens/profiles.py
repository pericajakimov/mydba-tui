"""
Connection profiles screen.

Displays the list of saved connection profiles and allows
the user to add, edit, delete, and select profiles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from mydba_tui.config.profiles import load_profiles, remove_profile, save_profiles
from mydba_tui.models.profile import Profile
from mydba_tui.ui.screens.password_prompt import Credentials, CredentialsPromptScreen
from mydba_tui.ui.screens.profile_form import ProfileFormScreen
from mydba_tui.ui.widgets import ConfirmDialog, StatusBar

if TYPE_CHECKING:
    from mysql.connector.errors import Error as MySQLError

    from mydba_tui.server import ServerInfo

# Environment colors as documented in 05-connection-manager.md
ENVIRONMENT_COLORS = {
    "prod": "red",
    "stage": "#ff8c00",
    "qa": "#5cacee",
    "dev": "green",
}


class ProfilesScreen(Screen[None]):
    """Connection profile list and management screen."""

    BINDINGS = [
        Binding("a", "add_profile", "Add"),
        Binding("e", "edit_profile", "Edit"),
        Binding("d", "delete_profile", "Delete"),
        Binding("escape", "go_back", "Back"),
        Binding("f10", "quit", "Exit"),
    ]

    CSS = """
    #profiles-container {
        height: 1fr;
        padding: 1 2;
    }

    #profile-list {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        """Build the profiles screen layout."""
        yield Header()
        yield StatusBar(id="status-bar")
        with Vertical(id="profiles-container"):
            yield Static("[b]Connection Profiles[/b]\n", id="profiles-title")
            yield ListView(id="profile-list")
        yield Footer()

    def on_mount(self) -> None:
        """Load and display profiles on mount."""
        self._refresh_list()
        self._sync_status_bar()

    def on_screen_resume(self) -> None:
        """Update status bar when screen becomes visible."""
        self._sync_status_bar()

    def _sync_status_bar(self) -> None:
        """Sync status bar with current connection state."""
        status = getattr(self.app, "connection_status", "")
        if status:
            self.query_one("#status-bar", StatusBar).status_text = status

    def _refresh_list(self) -> None:
        """Reload profiles from disk and update the list view."""
        list_view = self.query_one("#profile-list", ListView)
        list_view.clear()

        profiles = load_profiles()

        if not profiles:
            list_view.append(
                ListItem(Label("[dim]No profiles configured. Press 'a' to add one.[/dim]"))
            )
            return

        # Group by environment
        grouped: dict[str, list[Profile]] = {}
        for profile in profiles:
            env = profile.environment
            if env not in grouped:
                grouped[env] = []
            grouped[env].append(profile)

        # Display order: prod, stage, qa, dev
        env_order = ["prod", "stage", "qa", "dev"]
        for env in env_order:
            if env not in grouped:
                continue
            color = ENVIRONMENT_COLORS.get(env, "white")
            list_view.append(
                ListItem(
                    Label(f"[{color} bold]{env.upper()}[/{color} bold]"),
                )
            )
            for profile in grouped[env]:
                list_view.append(
                    ListItem(
                        Label(f"  {profile.name}"),
                        name=profile.name,
                    )
                )

    def _get_selected_profile_name(self) -> str | None:
        """Get the name of the currently selected profile."""
        list_view = self.query_one("#profile-list", ListView)
        if list_view.highlighted_child is None:
            return None
        return list_view.highlighted_child.name

    def action_add_profile(self) -> None:
        """Open the form to add a new profile."""

        def on_result(profile: Profile | None) -> None:
            if profile is not None:
                profiles = load_profiles()
                profiles.append(profile)
                save_profiles(profiles)
                self._refresh_list()

        self.app.push_screen(ProfileFormScreen(), callback=on_result)

    def action_edit_profile(self) -> None:
        """Open the form to edit the selected profile."""
        name = self._get_selected_profile_name()
        if name is None:
            return

        profiles = load_profiles()
        profile = next((p for p in profiles if p.name == name), None)
        if profile is None:
            return

        def on_result(updated: Profile | None) -> None:
            if updated is not None:
                current_profiles = load_profiles()
                for i, p in enumerate(current_profiles):
                    if p.name == name:
                        current_profiles[i] = updated
                        break
                save_profiles(current_profiles)
                self._refresh_list()

        self.app.push_screen(ProfileFormScreen(profile), callback=on_result)

    def action_delete_profile(self) -> None:
        """Delete the selected profile after confirmation."""
        name = self._get_selected_profile_name()
        if name is None:
            return

        def on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                try:
                    remove_profile(name)
                except ValueError:
                    pass
                self._refresh_list()

        self.app.push_screen(
            ConfirmDialog(f"Delete profile '{name}'?"),
            callback=on_confirm,
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle Enter on a list item — attempt connection."""
        self.action_select_profile()

    def action_select_profile(self) -> None:
        """Select a profile and attempt connection."""
        name = self._get_selected_profile_name()
        if name is None:
            return

        profiles = load_profiles()
        profile = next((p for p in profiles if p.name == name), None)
        if profile is None:
            return

        # Resolve effective credentials from all sources
        username, password = self._resolve_credentials(profile)

        if username and password:
            # All credentials available — connect directly
            self._attempt_connection(profile, username, password)
        else:
            # Missing info — prompt only for what's needed
            self.app.push_screen(
                CredentialsPromptScreen(
                    profile_name=profile.name,
                    host=profile.host,
                    username=username,
                    password=password,
                ),
                callback=lambda creds: self._on_credentials(profile, creds),
            )

    @staticmethod
    def _resolve_credentials(profile: Profile) -> tuple[str, str]:
        """Determine effective username and password from all sources.

        Priority:
        1. Explicit profile fields.
        2. login_path (we can't read .mylogin.cnf, so assume it provides both).
        3. option_file or ~/.my.cnf parsed for [client] credentials.

        Returns:
            Tuple of (username, password) with empty string for missing values.
        """
        from mydba_tui.connection.mycnf import read_mycnf_credentials

        # Start with profile values
        username = profile.username
        password = profile.password

        # login_path — assume it provides everything (encrypted, can't read)
        if profile.login_path:
            return username or "login_path", password or "login_path"

        # Read from config files to fill gaps
        if not username or not password:
            creds = read_mycnf_credentials(
                option_file=profile.option_file,
                option_group=profile.option_group,
            )
            if not username and creds.user:
                username = creds.user
            if not password and creds.password:
                password = creds.password

        return username, password

    def _on_credentials(self, profile: Profile, creds: Credentials | None) -> None:
        """Handle credentials prompt result."""
        if creds is None:
            return
        self._attempt_connection(profile, creds.username, creds.password)

    def _attempt_connection(self, profile: Profile, username: str, password: str) -> None:
        """Try to connect using the profile and handle success/failure.

        Runs the connection in a background worker so the UI stays
        responsive and can show the "Connecting..." notification.
        """
        # Override profile credentials with runtime values only if provided
        if username:
            profile.username = username

        # Show connecting status
        self.query_one(
            "#status-bar", StatusBar
        ).status_text = f"[dim]Connecting to {profile.name}...[/dim]"
        self._connect_worker(profile, password)

    @work(thread=True)
    def _connect_worker(self, profile: Profile, password: str) -> None:
        """Background worker that performs the actual connection."""
        from mysql.connector.errors import Error as MySQLError

        from mydba_tui.connection import connect

        try:
            connection = connect(profile, password)
        except MySQLError as e:
            # Schedule UI update on the main thread
            self.app.call_from_thread(self._on_connect_failure, profile, e)
            return

        self.app.call_from_thread(self._on_connect_success, profile, connection)

    def _on_connect_success(self, profile: Profile, connection: object) -> None:
        """Handle successful connection (called on main thread)."""
        from mydba_tui.server import detect

        server_info = detect(connection)  # type: ignore[arg-type]
        self.app.db_connection = connection  # type: ignore[attr-defined]
        self.app.active_profile = profile  # type: ignore[attr-defined]
        self.app.server_info = server_info  # type: ignore[attr-defined]

        # Build status text with colored environment
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

        self.app.connection_status = status  # type: ignore[attr-defined]
        self.notify(f"Connected to {profile.name}", severity="information")
        self.app.pop_screen()

    def _on_connect_failure(self, profile: Profile, error: MySQLError) -> None:
        """Handle connection failure (called on main thread)."""
        # Reset status bar
        status = getattr(self.app, "connection_status", "")
        self.query_one("#status-bar", StatusBar).status_text = (
            status if status else "[dim]Not connected[/dim]"
        )

        # Error codes 1044, 1045, 1698 are auth-related
        if error.errno in (1044, 1045, 1698):
            self.app.push_screen(
                CredentialsPromptScreen(
                    profile_name=profile.name,
                    host=profile.host,
                    username=profile.username,
                    password="",
                ),
                callback=lambda creds: self._on_credentials(profile, creds),
            )
            self.notify(str(error.msg), severity="error", timeout=5)
        else:
            self.notify(
                f"Connection failed:\n{error}",
                severity="error",
                timeout=10,
            )

    def action_go_back(self) -> None:
        """Return to the home screen."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()


def _format_vendor(server_info: ServerInfo) -> str:
    """Format the vendor name and version for display.

    Args:
        server_info: Detected server information.

    Returns:
        Formatted string like "Aurora 3.04.3 (InnoDB 8.0.44)" or "MySQL 8.4.0".
    """
    vendor_names = {
        "oracle": "MySQL",
        "percona": "Percona",
        "pxc": "PXC",
        "aurora": "Aurora",
        "mariadb": "MariaDB",
    }
    name = vendor_names.get(server_info.vendor, "MySQL")

    if server_info.vendor == "aurora" and server_info.aurora_version:
        version_str = f"{name} {server_info.aurora_version}"
        # Show InnoDB version for Aurora v3 (version starts with "3.")
        if server_info.aurora_version.startswith("3.") and server_info.innodb_version:
            version_str += f" (InnoDB {server_info.innodb_version})"
        return version_str

    return f"{name} {server_info.version}"
