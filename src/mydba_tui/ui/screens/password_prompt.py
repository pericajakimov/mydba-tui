"""
Credentials prompt screen.

A modal that prompts for username and/or password before connecting.
Fields are pre-populated from the profile when available.
"""

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


@dataclass(slots=True)
class Credentials:
    """Username and password entered by the user."""

    username: str
    password: str


class CredentialsPromptScreen(ModalScreen[Credentials | None]):
    """Modal credentials prompt.

    Pre-populates username and password from the profile.
    The user can modify both fields before connecting.

    Returns Credentials on submit, or None if cancelled.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    CredentialsPromptScreen {
        align: center middle;
    }

    #creds-container {
        width: 50;
        height: auto;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    #creds-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
    }

    #creds-info {
        color: $text-muted;
        padding-bottom: 1;
    }

    .creds-label {
        margin-top: 1;
    }

    #creds-buttons {
        margin-top: 1;
        align: center middle;
    }
    """

    def __init__(
        self,
        profile_name: str,
        host: str,
        username: str = "",
        password: str = "",
    ) -> None:
        """Initialize the prompt.

        Args:
            profile_name: Name of the profile being connected.
            host: Host shown in the prompt for context.
            username: Pre-populated username (editable).
            password: Pre-populated password (editable).
        """
        super().__init__()
        self._profile_name = profile_name
        self._host = host
        self._username = username
        self._password = password

    def compose(self) -> ComposeResult:
        """Build the prompt layout."""
        with Vertical(id="creds-container"):
            yield Static("Connect", id="creds-title")
            yield Static(
                f"[dim]{self._profile_name}[/dim] — {self._host}",
                id="creds-info",
            )

            yield Label("Username:", classes="creds-label")
            yield Input(
                value=self._username,
                placeholder="MySQL username",
                id="input-username",
            )

            yield Label("Password:", classes="creds-label")
            yield Input(
                value=self._password,
                placeholder="",
                password=True,
                id="input-password",
            )

            yield Button("Connect", variant="primary", id="btn-connect")

    def on_mount(self) -> None:
        """Focus the first empty field."""
        username_input = self.query_one("#input-username", Input)
        password_input = self.query_one("#input-password", Input)

        if not username_input.value:
            username_input.focus()
        else:
            password_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in input fields."""
        if event.input.id == "input-username":
            # Move focus to password field
            self.query_one("#input-password", Input).focus()
        elif event.input.id == "input-password":
            self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Connect button."""
        self._submit()

    def _submit(self) -> None:
        """Validate and submit credentials."""
        username = self.query_one("#input-username", Input).value.strip()
        password = self.query_one("#input-password", Input).value

        if not username:
            self.notify("Username is required.", severity="error")
            self.query_one("#input-username", Input).focus()
            return

        self.dismiss(Credentials(username=username, password=password))

    def action_cancel(self) -> None:
        """Cancel the prompt."""
        self.dismiss(None)
