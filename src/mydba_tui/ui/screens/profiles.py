"""
Connection profiles screen.

Displays the list of saved connection profiles and allows
the user to add, edit, delete, and select profiles.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from mydba_tui.config.profiles import load_profiles, remove_profile, save_profiles
from mydba_tui.models.profile import Profile
from mydba_tui.ui.screens.profile_form import ProfileFormScreen
from mydba_tui.ui.widgets import ConfirmDialog

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
        Binding("enter", "select_profile", "Connect"),
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
        with Vertical(id="profiles-container"):
            yield Static("[b]Connection Profiles[/b]\n", id="profiles-title")
            yield ListView(id="profile-list")
        yield Footer()

    def on_mount(self) -> None:
        """Load and display profiles on mount."""
        self._refresh_list()

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

    def action_select_profile(self) -> None:
        """Select a profile for connection (placeholder)."""
        name = self._get_selected_profile_name()
        if name is None:
            return
        self.notify(f"Connection to '{name}' not yet implemented.", title="Connect")

    def action_go_back(self) -> None:
        """Return to the home screen."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()
