"""
Confirmation dialog.

A simple modal that asks the user to confirm or cancel an action.
Default focus is on the safe option (No) to prevent accidental
destructive actions.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmDialog(ModalScreen[bool]):
    """A yes/no confirmation dialog.

    Focus defaults to the No button. The user must Tab to Yes
    and press Enter to confirm a destructive action.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    ConfirmDialog {
        align: center middle;
    }

    #confirm-container {
        width: 50;
        height: auto;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    #confirm-message {
        text-align: center;
        padding: 1 0;
    }

    #confirm-buttons {
        margin-top: 1;
        align: center middle;
        height: auto;
        layout: horizontal;
    }

    #confirm-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, message: str) -> None:
        """Initialize the dialog.

        Args:
            message: The confirmation message to display.
        """
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        """Build the dialog layout."""
        with Vertical(id="confirm-container"):
            yield Static(self._message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("No", variant="primary", id="btn-no")
                yield Button("Yes", variant="error", id="btn-yes")

    def on_mount(self) -> None:
        """Focus the No button by default."""
        self.query_one("#btn-no", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Cancel (Esc)."""
        self.dismiss(False)
