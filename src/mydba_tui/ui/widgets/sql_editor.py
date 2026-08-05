"""
SQL Editor widget with inline autocomplete.

Extends Textual's TextArea with a non-focusable completion popup.
The editor always retains focus — special keys (Tab, Enter, Up, Down, Esc)
are intercepted when the popup is visible.
"""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static, TextArea


class CompletionPopup(Widget):
    """A non-focusable completion popup that displays suggestions."""

    DEFAULT_CSS = """
    CompletionPopup {
        display: none;
        position: absolute;
        width: 50;
        max-height: 10;
        border: solid $accent;
        background: $surface;
        overflow-y: auto;
        layer: overlay;
    }

    CompletionPopup.visible {
        display: block;
    }

    .completion-item {
        padding: 0 1;
    }

    .completion-item-selected {
        padding: 0 1;
        background: $accent;
        color: $text;
    }
    """

    can_focus = False

    highlighted: reactive[int] = reactive(0)

    def __init__(self) -> None:
        super().__init__()
        self._items: list[str] = []
        self._insert_texts: list[str] = []
        self._kinds: list[str] = []

    def set_items(
        self, display_items: list[str], insert_texts: list[str], kinds: list[str]
    ) -> None:
        """Set the completion items to display."""
        self._items = display_items
        self._insert_texts = insert_texts
        self._kinds = kinds
        self.highlighted = 0
        self._refresh_display()

    def get_selected_text(self) -> str | None:
        """Get the insert text of the currently highlighted item."""
        if 0 <= self.highlighted < len(self._insert_texts):
            return self._insert_texts[self.highlighted]
        return None

    def get_selected_kind(self) -> str:
        """Get the kind of the currently highlighted item."""
        if 0 <= self.highlighted < len(self._kinds):
            return self._kinds[self.highlighted]
        return ""

    @property
    def item_count(self) -> int:
        return len(self._items)

    def move_up(self) -> None:
        """Move highlight up."""
        if self._items:
            self.highlighted = max(0, self.highlighted - 1)
            self._refresh_display()

    def move_down(self) -> None:
        """Move highlight down."""
        if self._items:
            self.highlighted = min(len(self._items) - 1, self.highlighted + 1)
            self._refresh_display()

    def show(self) -> None:
        """Show the popup."""
        self.add_class("visible")

    def hide(self) -> None:
        """Hide the popup."""
        self.remove_class("visible")

    @property
    def is_visible(self) -> bool:
        return self.has_class("visible")

    def _refresh_display(self) -> None:
        """Rebuild the display content."""
        self.remove_children()
        for i, item in enumerate(self._items[:15]):  # Show max 15 items
            cls = (
                "completion-item-selected"
                if i == self.highlighted
                else "completion-item"
            )
            self.mount(Static(item, classes=cls))


class _CompletingTextArea(TextArea):
    """TextArea subclass that intercepts keys for completion."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._completion_active = False
        self._on_accept_completion: object = None
        self._on_dismiss_completion: object = None
        self._on_move_up: object = None
        self._on_move_down: object = None

    async def _on_key(self, event: events.Key) -> None:
        """Intercept keys before TextArea processes them."""
        if self._completion_active:
            if event.key == "tab" or event.key == "enter":
                if self._on_accept_completion:
                    self._on_accept_completion()  # type: ignore[operator]
                event.prevent_default()
                event.stop()
                return
            elif event.key == "escape":
                if self._on_dismiss_completion:
                    self._on_dismiss_completion()  # type: ignore[operator]
                event.prevent_default()
                event.stop()
                return
            elif event.key == "down":
                if self._on_move_down:
                    self._on_move_down()  # type: ignore[operator]
                event.prevent_default()
                event.stop()
                return
            elif event.key == "up":
                if self._on_move_up:
                    self._on_move_up()  # type: ignore[operator]
                event.prevent_default()
                event.stop()
                return

        # Default: let TextArea handle the key
        await super()._on_key(event)


class SQLEditor(Vertical):
    """SQL Editor with integrated autocomplete popup.

    Wraps a TextArea and a CompletionPopup. The TextArea always has focus.
    When the popup is visible, Tab/Enter accept the selection,
    Up/Down navigate, Esc dismisses, and all other keys go to the editor.
    """

    DEFAULT_CSS = """
    SQLEditor {
        height: 100%;
    }

    SQLEditor > _CompletingTextArea {
        height: 1fr;
    }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._skip_next_trigger = False

    def compose(self) -> ComposeResult:
        ta = _CompletingTextArea.code_editor("", language="sql")
        ta.id = "sql-editor-inner"
        ta._on_accept_completion = self._accept_current  # type: ignore[attr-defined]
        ta._on_dismiss_completion = self.hide_completions  # type: ignore[attr-defined]
        ta._on_move_up = lambda: self.popup.move_up()  # type: ignore[attr-defined]
        ta._on_move_down = lambda: self.popup.move_down()  # type: ignore[attr-defined]
        yield ta
        yield CompletionPopup()

    @property
    def editor(self) -> TextArea:
        """Get the inner TextArea."""
        return self.query_one("#sql-editor-inner", TextArea)

    @property
    def popup(self) -> CompletionPopup:
        """Get the completion popup."""
        return self.query_one(CompletionPopup)

    def show_completions(
        self, display_items: list[str], insert_texts: list[str], kinds: list[str]
    ) -> None:
        """Show the completion popup with items, positioned near cursor."""
        if not display_items:
            self.hide_completions()
            return
        self.popup.set_items(display_items, insert_texts, kinds)

        # Position popup relative to cursor
        editor = self.editor
        cursor_row, cursor_col = editor.cursor_location
        visible_row = cursor_row - editor.scroll_offset.y
        editor_height = editor.size.height
        editor_width = editor.size.width
        popup_width = 50

        # Use fixed popup height for consistent positioning
        popup_height = 12  # max-height(10) + border(2)

        # Check if popup fits below (need visible_row + 2 + popup_height <= editor_height)
        if visible_row + 2 + popup_height <= editor_height:
            # Fits below — show 2 rows under cursor
            y = visible_row + 2
        else:
            # Doesn't fit below — show above: cursor_line - 1 - popup_height
            y = visible_row - 1 - popup_height + 4
            if y < 0:
                y = 0

        # Horizontal: align with cursor, cap to not overflow
        x = min(cursor_col, max(editor_width - popup_width, 0))

        self.popup.styles.offset = (x, y)
        self.popup.show()
        # Tell the TextArea that completion is active
        editor = self.query_one("#sql-editor-inner", _CompletingTextArea)
        editor._completion_active = True

    def hide_completions(self) -> None:
        """Hide the completion popup."""
        self.popup.hide()
        try:
            editor = self.query_one("#sql-editor-inner", _CompletingTextArea)
            editor._completion_active = False
        except Exception:
            pass

    def _accept_current(self) -> None:
        """Accept the currently highlighted completion."""
        text = self.popup.get_selected_text()
        kind = self.popup.get_selected_kind()
        if text:
            # Add space only after keywords and types (not after objects/functions)
            if kind in ("keyword", "type") and not text.endswith("("):
                text = text + " "
            self._skip_next_trigger = True
            self._do_insert(text)
        self.hide_completions()

    def _do_insert(self, text: str) -> None:
        """Insert the accepted completion text, replacing the current prefix."""
        import re

        editor = self.editor
        cursor_row, cursor_col = editor.cursor_location
        line = str(editor.get_line(cursor_row))
        text_before = line[:cursor_col]

        # Find prefix to replace
        dot_match = re.search(r"`?(\w+)`?\.\s*`?(\w*)$", text_before)
        if dot_match:
            prefix_len = len(dot_match.group(2) or "")
        else:
            i = len(text_before) - 1
            while i >= 0 and (text_before[i].isalnum() or text_before[i] == "_"):
                i -= 1
            prefix_len = len(text_before) - (i + 1)

        start = (cursor_row, cursor_col - prefix_len)
        end = (cursor_row, cursor_col)
        editor.replace(text, start, end)
