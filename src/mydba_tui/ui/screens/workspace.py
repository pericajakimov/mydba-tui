"""
SQL Workspace screen.

Provides the interactive SQL editor and execution workspace.
Results are displayed with timestamp and SQL for each block.
A session log file is maintained in ~/.config/mydba/logs/sessions/
and auto-deleted on clean exit unless explicitly saved.
"""

import os
import re
import time as _time
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from rich.markup import escape as rich_escape
from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static, TextArea

from mydba_tui.ui.widgets import StatusBar

_SESSIONS_DIR = Path.home() / ".config" / "mydba" / "logs" / "sessions"

# Display row limits (cycle through with Ctrl+R)
_ROW_LIMITS = [100, 500, 1000, 5000, 10000, 50000, 100000, 0]  # 0 = no limit
_ROW_LIMIT_LABELS = ["100", "500", "1K", "5K", "10K", "50K", "100K", "No limit"]


class WorkspaceScreen(Screen[None]):
    """SQL Workspace — interactive SQL editor and results viewer."""

    BINDINGS = [
        Binding("f5", "execute", "Execute", key_display="F5", priority=True),
        Binding("f7", "explain", "Explain", key_display="F7", priority=True),
        Binding(
            "shift+f7", "explain_json", "Explain JSON",
            key_display="⇧F7", priority=True,
        ),
        Binding(
            "f8", "explain_analyze", "Analyze",
            key_display="F8", priority=True,
        ),
        Binding(
            "ctrl+s", "save_file", "Save SQL",
            key_display="^S", priority=True,
        ),
        Binding(
            "ctrl+o", "load_file", "Open SQL",
            key_display="^O", priority=True,
        ),
        Binding(
            "ctrl+l", "clear_results", "Clear",
            key_display="^L", priority=True,
        ),
        Binding(
            "ctrl+r", "cycle_row_limit", "Row Limit",
            key_display="^R", priority=True,
        ),
        Binding(
            "ctrl+shift+s", "save_log", "Save Log",
            key_display="^⇧S", priority=True,
        ),
        Binding(
            "f6", "switch_focus", "Switch Panel",
            key_display="F6", priority=True,
        ),
        Binding("f10", "quit", "Exit", key_display="F10", priority=True),
        Binding("escape", "go_back", "Back", key_display="Esc"),
    ]

    CSS = """
    #workspace-layout {
        height: 1fr;
    }

    #sql-editor {
        height: 40%;
        min-height: 5;
        border-bottom: solid $panel-darken-1;
    }

    #results-panel {
        height: 60%;
        overflow-x: auto;
        overflow-y: auto;
    }

    .result-block {
        padding: 0 1;
        margin-bottom: 1;
    }

    .result-data {
        padding: 0 1;
        margin-bottom: 1;
    }

    .result-info {
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        """Initialize the workspace."""
        super().__init__()
        self._file_path: str = ""
        self._focus_on_editor: bool = True
        self._result_count: int = 0
        self._session_log_path: Path | None = None
        self._session_saved: bool = False
        self._row_limit_idx: int = 2  # Default: 1000
        self._results_store: list[tuple[list[str], list[Any]]] = []

    def compose(self) -> ComposeResult:
        """Build the workspace layout."""
        yield Header()
        yield StatusBar(id="status-bar")

        with Vertical(id="workspace-layout"):
            yield TextArea.code_editor(
                "",
                language="sql",
                id="sql-editor",
            )
            yield ScrollableContainer(
                Static(
                    "[dim]Press F5 to execute SQL. "
                    "F7 for EXPLAIN. F8 for EXPLAIN ANALYZE.[/dim]",
                    classes="result-info",
                ),
                id="results-panel",
            )

        yield Footer()

    def on_mount(self) -> None:
        """Focus the editor on mount and apply custom SQL theme."""
        from mydba_tui.ui.sql_theme import SQL_THEME, SQL_THEME_NAME

        self._sync_status_bar()
        editor = self.query_one("#sql-editor", TextArea)
        editor.register_theme(SQL_THEME)
        editor.theme = SQL_THEME_NAME
        editor.focus()

    def on_screen_resume(self) -> None:
        """Update status bar when returning to this screen."""
        self._sync_status_bar()

    def _sync_status_bar(self) -> None:
        """Sync status bar with current connection state."""
        status = getattr(self.app, "connection_status", "")
        if status:
            self.query_one("#status-bar", StatusBar).status_text = status

    # --- Session Log ---

    def _ensure_session_log(self) -> None:
        """Create the session log file on first execution."""
        if self._session_log_path is not None:
            return

        _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._session_log_path = _SESSIONS_DIR / f"session_{timestamp}.log"

        # Create with restricted permissions (owner only)
        fd = os.open(
            str(self._session_log_path),
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )
        os.close(fd)

        # Write header with connection info
        header_lines = [
            "# mydba session log",
            f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        conn_status = getattr(self.app, "connection_status", "")
        if conn_status:
            # Strip Rich markup for plain text log
            from rich.text import Text

            plain_status = Text.from_markup(conn_status).plain
            header_lines.append(f"# Connection: {plain_status.strip()}")

        header_lines.append("")
        self._session_log_path.write_text(
            "\n".join(header_lines) + "\n", encoding="utf-8"
        )

    def _log_to_session(
        self,
        sql: str,
        result_text: str,
        duration: float,
    ) -> None:
        """Append an execution record with results to the session log."""
        if self._session_log_path is None:
            return

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"-- [{ts}] ({duration:.3f}s)\n"
            f"{sql};\n\n"
            f"{result_text}\n\n"
        )
        try:
            with open(self._session_log_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass

    def _cleanup_session_log(self) -> None:
        """Delete the session log if it wasn't explicitly saved."""
        if self._session_log_path and not self._session_saved:
            try:
                self._session_log_path.unlink(missing_ok=True)
            except Exception:
                pass

    # --- Execution ---

    def action_execute(self) -> None:
        """Execute the selected text or entire editor contents."""
        sql = self._get_sql_to_execute()
        if not sql.strip():
            return
        self._ensure_session_log()
        self._run_in_worker(sql)

    def action_explain(self) -> None:
        """Run EXPLAIN on the selected text or editor contents."""
        sql = self._get_sql_to_execute()
        if not sql.strip():
            return
        self._ensure_session_log()
        self._run_in_worker(f"EXPLAIN {sql.strip().rstrip(';')}")

    def action_explain_json(self) -> None:
        """Run EXPLAIN FORMAT=JSON on the selected text or editor contents."""
        sql = self._get_sql_to_execute()
        if not sql.strip():
            return
        self._ensure_session_log()
        self._run_in_worker(f"EXPLAIN FORMAT=JSON {sql.strip().rstrip(';')}")

    def action_explain_analyze(self) -> None:
        """Run EXPLAIN ANALYZE on the selected text or editor contents."""
        sql = self._get_sql_to_execute()
        if not sql.strip():
            return
        self._ensure_session_log()
        self._run_in_worker(f"EXPLAIN ANALYZE {sql.strip().rstrip(';')}")

    def _get_sql_to_execute(self) -> str:
        """Get SQL text: selected text if any, otherwise full editor contents."""
        editor = self.query_one("#sql-editor", TextArea)
        selected = editor.selected_text
        if selected and selected.strip():
            return selected
        return editor.text

    def _run_in_worker(self, sql: str) -> None:
        """Run SQL execution in a background thread to keep UI responsive."""
        self._append_status("Executing...")
        self.run_worker(
            lambda: self._execute_in_thread(sql),
            name="sql_exec",
            exclusive=True,
            thread=True,
        )

    def _execute_in_thread(self, sql: str) -> None:
        """Execute SQL statements (runs in background thread)."""
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.logging import log_sql

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self.app.call_from_thread(self._remove_status)
            self.app.call_from_thread(
                self._append_error, "Not connected to a database."
            )
            return

        # Split into individual statements (handles ; and \G)
        statements = self._split_statements(sql)

        for stmt, vertical in statements:
            stmt = stmt.strip()
            if not stmt:
                continue

            self.app.call_from_thread(
                self._update_status, f"Executing: {stmt[:60]}..."
            )

            start = _time.perf_counter()
            try:
                cursor = conn_result.connection.cursor(buffered=True)
                cursor.execute(stmt)

                duration = _time.perf_counter() - start
                log_sql(stmt, duration, "workspace")

                if cursor.description:
                    col_names = [desc[0] for desc in cursor.description]

                    self.app.call_from_thread(
                        self._update_status, "Fetching results..."
                    )

                    # Fetch ALL rows (stored for potential export)
                    rows = cursor.fetchall()
                    cursor.close()

                    total_rows = len(rows)
                    self.app.call_from_thread(
                        self._update_status,
                        f"Rendering {total_rows:,} rows...",
                    )

                    # Store full result set for export
                    self._results_store.append((col_names, rows))

                    # Determine display limit
                    limit = _ROW_LIMITS[self._row_limit_idx]
                    if limit > 0 and total_rows > limit:
                        display_rows = rows[:limit]
                        truncated = True
                    else:
                        display_rows = rows
                        truncated = False

                    self.app.call_from_thread(self._remove_status)
                    self.app.call_from_thread(
                        self._append_result_set,
                        stmt,
                        col_names,
                        display_rows,
                        duration,
                        vertical,
                        truncated,
                        total_rows,
                    )
                else:
                    affected = cursor.rowcount
                    cursor.close()
                    summary = f"{affected} row(s) affected"

                    self.app.call_from_thread(self._remove_status)
                    self.app.call_from_thread(
                        self._append_info, stmt, summary, duration
                    )
                    self._log_to_session(stmt, summary, duration)

            except Exception as e:
                duration = _time.perf_counter() - start
                log_sql(stmt, duration, "workspace.error")
                self.app.call_from_thread(self._remove_status)
                self.app.call_from_thread(self._append_error, str(e), stmt)
                self._log_to_session(stmt, f"ERROR: {e}", duration)

    def _split_statements(self, sql: str) -> list[tuple[str, bool]]:
        r"""Split SQL text into individual statements.

        Handles both ; and \G as terminators.
        Returns list of (statement, vertical_output) tuples.
        """
        results: list[tuple[str, bool]] = []
        parts = re.split(r"(;|\\G)", sql)

        current = ""
        for part in parts:
            if part == ";":
                if current.strip():
                    results.append((current.strip(), False))
                current = ""
            elif part == "\\G":
                if current.strip():
                    results.append((current.strip(), True))
                current = ""
            else:
                current += part

        # Handle trailing statement without terminator
        if current.strip():
            results.append((current.strip(), False))

        return results

    # --- Status Indicator ---

    def _append_status(self, message: str) -> None:
        """Show a status message at the bottom of results."""
        panel = self.query_one("#results-panel", ScrollableContainer)
        panel.mount(
            Static(f"[bold yellow]⏳ {message}[/bold yellow]", id="exec-status")
        )
        panel.scroll_end()

    def _update_status(self, message: str) -> None:
        """Update the status message."""
        try:
            status = self.query_one("#exec-status", Static)
            status.update(f"[bold yellow]⏳ {message}[/bold yellow]")
        except Exception:
            pass

    def _remove_status(self) -> None:
        """Remove the status indicator."""
        try:
            self.query_one("#exec-status", Static).remove()
        except Exception:
            pass

    # --- Result Display ---

    def _append_result_set(
        self,
        sql: str,
        col_names: list[str],
        rows: list[Any],
        duration: float,
        vertical: bool = False,
        truncated: bool = False,
        total_rows: int = 0,
    ) -> None:
        """Append a result set to the results panel."""
        self._result_count += 1
        panel = self.query_one("#results-panel", ScrollableContainer)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        displayed = len(rows)
        if truncated:
            limit_label = _ROW_LIMIT_LABELS[self._row_limit_idx]
            row_label = (
                f"{displayed:,} of {total_rows:,} rows shown"
                f" (display limit: {limit_label}, Ctrl+R to change)"
            )
        else:
            row_label = f"{displayed:,} row{'s' if displayed != 1 else ''}"
        summary = f"{row_label} ({duration:.3f}s)"

        # Header (with markup): timestamp + SQL
        header_lines: list[str] = []
        header_lines.append(f"[bold]── {ts} ──[/bold]")
        header_lines.append(f"[dim]{rich_escape(sql)};[/dim]")

        panel.mount(Static("\n".join(header_lines), classes="result-block"))

        # Data (colored Rich Text)
        data_lines: list[str] = []
        if not rows:
            panel.mount(
                Static("[dim]Empty set.[/dim]", classes="result-block")
            )
        elif vertical:
            # Vertical output (\G style) — colored
            data_text = _build_vertical_text(col_names, rows)
            data_widget = Static(data_text, classes="result-data")
            panel.mount(data_widget)
            # Plain text for log
            data_lines = _build_vertical_plain(col_names, rows)
        else:
            # Tabular output — colored
            result_format = getattr(
                getattr(self.app, "settings", None), "result_format", "mysql"
            )
            data_text = _build_table_text(col_names, rows, result_format)
            data_widget = Static(data_text, classes="result-data")
            data_widget.styles.width = "auto"
            panel.mount(data_widget)
            # Plain text for log
            data_lines = _build_table_plain(col_names, rows, result_format)

        # Summary AFTER results
        panel.mount(
            Static(f"[bold]{summary}[/bold]\n", classes="result-block")
        )

        panel.scroll_end()

        # Log to session file — mirrors displayed output
        self._log_result_to_session(sql, data_lines, summary, duration)

    def _log_result_to_session(
        self,
        sql: str,
        data_lines: list[str],
        summary: str,
        duration: float,
    ) -> None:
        """Log a result set to the session file — mirrors the displayed output."""
        if self._session_log_path is None:
            return

        result_text = "\n".join(data_lines) + f"\n\n{summary}"
        self._log_to_session(sql, result_text, duration)

    def _append_info(self, sql: str, message: str, duration: float) -> None:
        """Append an info message (DML result) to the results panel."""
        self._result_count += 1
        panel = self.query_one("#results-panel", ScrollableContainer)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = (
            f"[bold]── {ts} ──[/bold]\n"
            f"[dim]{rich_escape(sql)};[/dim]\n\n"
            f"[bold]{message} ({duration:.3f}s)[/bold]\n"
        )
        panel.mount(Static(content, classes="result-block"))
        panel.scroll_end()

    def _append_error(self, error: str, sql: str = "") -> None:
        """Append an error message to the results panel."""
        self._result_count += 1
        panel = self.query_one("#results-panel", ScrollableContainer)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines: list[str] = [f"[bold]── {ts} ──[/bold]"]
        if sql:
            lines.append(f"[dim]{rich_escape(sql)};[/dim]")
            lines.append("")
        lines.append(
            f"[bold red]ERROR:[/bold red] [red]{rich_escape(error)}[/red]"
        )
        lines.append("")

        panel.mount(Static("\n".join(lines), classes="result-block"))
        panel.scroll_end()

    # --- File Operations ---

    def action_save_file(self) -> None:
        """Save editor contents to a file."""
        editor = self.query_one("#sql-editor", TextArea)
        text = editor.text

        if not text.strip():
            self.notify("Nothing to save.", severity="warning")
            return

        if self._file_path:
            try:
                Path(self._file_path).write_text(text, encoding="utf-8")
                self.notify(f"Saved to {self._file_path}")
            except Exception as e:
                self.notify(f"Save failed: {e}", severity="error")
        else:
            self.app.push_screen(
                _FilePromptScreen("Save as:", self._do_save),
            )

    def _do_save(self, path: str) -> None:
        """Perform the save operation."""
        if not path:
            return
        editor = self.query_one("#sql-editor", TextArea)
        try:
            Path(path).write_text(editor.text, encoding="utf-8")
            self._file_path = path
            self.notify(f"Saved to {path}")
        except Exception as e:
            self.notify(f"Save failed: {e}", severity="error")

    def action_load_file(self) -> None:
        """Load a SQL file into the editor."""
        self.app.push_screen(
            _FilePromptScreen("Open file:", self._do_load),
        )

    def _do_load(self, path: str) -> None:
        """Perform the load operation."""
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            editor = self.query_one("#sql-editor", TextArea)
            editor.clear()
            editor.insert(text)
            self._file_path = path
            self.notify(f"Loaded {path}")
        except Exception as e:
            self.notify(f"Load failed: {e}", severity="error")

    # --- Focus, Clear, and Exit ---

    def action_switch_focus(self) -> None:
        """Switch focus between editor and results panel."""
        self._focus_on_editor = not self._focus_on_editor
        if self._focus_on_editor:
            self.query_one("#sql-editor", TextArea).focus()
        else:
            self.query_one("#results-panel", ScrollableContainer).focus()

    def action_clear_results(self) -> None:
        """Clear all results from the results panel."""
        panel = self.query_one("#results-panel", ScrollableContainer)
        panel.remove_children()
        panel.mount(
            Static("[dim]Results cleared.[/dim]", classes="result-info")
        )
        self._result_count = 0
        self._results_store.clear()

    def action_cycle_row_limit(self) -> None:
        """Cycle through row display limits."""
        self._row_limit_idx = (self._row_limit_idx + 1) % len(_ROW_LIMITS)
        label = _ROW_LIMIT_LABELS[self._row_limit_idx]
        self.notify(f"Row display limit: {label}")

    def action_save_log(self) -> None:
        """Save session log to a user-chosen location."""
        if not self._session_log_path or not self._session_log_path.exists():
            self.notify("No session log to save.", severity="warning")
            return

        self.app.push_screen(
            _FilePromptScreen("Save log as:", self._do_save_log),
        )

    def _do_save_log(self, path: str) -> None:
        """Move session log to user-chosen path and continue writing there."""
        if not path:
            return
        try:
            import shutil

            shutil.move(str(self._session_log_path), path)
            self._session_log_path = Path(path)
            self._session_saved = True
            self.notify(f"Log moved to {path}")
        except Exception as e:
            self.notify(f"Save log failed: {e}", severity="error")

    def action_go_back(self) -> None:
        """Exit workspace and clean up session log if not saved."""
        self._cleanup_session_log()
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Exit the application."""
        self._cleanup_session_log()
        self.app.exit()


def _format_cell(val: Any) -> str:
    """Format a cell value for workspace display.

    Workspace shows full data:
    - Binary → always hex
    - Text → full content (no truncation)
    - NULL → literal "NULL" string
    """
    if val is None:
        return "NULL"
    if isinstance(val, (bytes, bytearray)):
        return "0x" + val.hex().upper()
    return str(val)


# --- Result coloring ---

_S_NULL = Style(color="#666666", italic=True)  # Gray — NULL
_S_NUMBER = Style(color="#b5cea8")  # Light green — integers
_S_DECIMAL = Style(color="#d7ba7d")  # Warm gold — decimals/floats
_S_STRING = Style(color="#ce9178")  # Orange — strings (same as SQL editor)
_S_DATE = Style(color="#4ec9b0")  # Teal — dates/times
_S_BINARY = Style(color="#c586c0")  # Purple — binary/hex
_S_BORDER = Style(color="#555555")  # Dark gray — table borders
_S_HEADER = Style(bold=True)  # Bold — column headers
_S_JSON_KEY = Style(color="#569cd6")  # Blue — JSON keys
_S_JSON_STRING = Style(color="#ce9178")  # Orange — JSON strings
_S_JSON_NUMBER = Style(color="#b5cea8")  # Light green — JSON numbers
_S_JSON_BOOL = Style(color="#7daf9c")  # Muted teal — JSON booleans/null
_S_JSON_BRACE = Style(color="#cccccc")  # Light gray — braces/brackets


def _cell_style(val: Any) -> Style:
    """Determine the display style for a cell value based on its Python type."""
    if val is None:
        return _S_NULL
    if isinstance(val, (bytes, bytearray)):
        return _S_BINARY
    if isinstance(val, int):
        return _S_NUMBER
    if isinstance(val, (float, Decimal)):
        return _S_DECIMAL
    if isinstance(val, (datetime, date, time, timedelta)):
        return _S_DATE
    # Check for date/time types from mysql-connector
    s = str(val)
    # Detect datetime-like strings (from cursor)
    if _looks_like_datetime(s):
        return _S_DATE
    return _S_STRING


def _looks_like_datetime(s: str) -> bool:
    """Quick check if a string looks like a date/datetime."""
    if len(s) >= 10 and s[4:5] == "-" and s[7:8] == "-":
        return True  # YYYY-MM-DD...
    if len(s) == 8 and s[2:3] == ":" and s[5:6] == ":":
        return True  # HH:MM:SS
    return False


def _is_json(s: str) -> bool:
    """Quick check if a string looks like JSON."""
    stripped = s.strip()
    if not stripped:
        return False
    if (stripped[0] == "{" and stripped[-1] == "}") or (
        stripped[0] == "[" and stripped[-1] == "]"
    ):
        import json

        try:
            json.loads(stripped)
            return True
        except (json.JSONDecodeError, ValueError):
            return False
    return False


_JSON_TOKEN_RE = re.compile(
    r"""
    (?P<string>"(?:[^"\\]|\\.)*")  |
    (?P<number>-?\d+\.?\d*(?:[eE][+-]?\d+)?)  |
    (?P<bool>true|false|null)  |
    (?P<brace>[{}\[\]])  |
    (?P<punct>[,:])  |
    (?P<ws>\s+)  |
    (?P<other>.)
    """,
    re.VERBOSE,
)


def _highlight_json(s: str) -> Text:
    """Highlight a JSON string with colors."""
    text = Text()
    # Track if previous non-ws token was a key (string followed by :)
    tokens = list(_JSON_TOKEN_RE.finditer(s))
    for idx, match in enumerate(tokens):
        token = match.group()
        kind = match.lastgroup

        if kind == "string":
            # Check if this string is a key (followed by :)
            is_key = False
            for lookahead in tokens[idx + 1 :]:
                if lookahead.lastgroup == "ws":
                    continue
                if lookahead.group() == ":":
                    is_key = True
                break
            if is_key:
                text.append(token, style=_S_JSON_KEY)
            else:
                text.append(token, style=_S_JSON_STRING)
        elif kind == "number":
            text.append(token, style=_S_JSON_NUMBER)
        elif kind == "bool":
            text.append(token, style=_S_JSON_BOOL)
        elif kind == "brace":
            text.append(token, style=_S_JSON_BRACE)
        elif kind == "punct":
            text.append(token, style=_S_JSON_BRACE)
        else:
            text.append(token)
    return text


def _styled_cell(val: Any) -> Text:
    """Create a styled Text for a single cell value."""
    s = _format_cell(val)
    style = _cell_style(val)

    # If it's a string value and looks like JSON, highlight it
    if style == _S_STRING and isinstance(val, str) and _is_json(val):
        return _highlight_json(val)

    t = Text(s)
    t.stylize(style)
    return t


def _build_table_text(
    col_names: list[str], rows: list[Any], fmt: str
) -> Text:
    """Build a colored Rich Text table from result data."""
    # Calculate widths and format cells
    col_widths = [len(name) for name in col_names]
    cell_strings: list[list[str]] = []
    for row in rows:
        str_row = []
        for i, val in enumerate(row):
            s = _format_cell(val)
            str_row.append(s)
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(s))
        cell_strings.append(str_row)

    text = Text()

    if fmt == "mysql":
        border = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        text.append(border + "\n", style=_S_BORDER)

        # Header
        text.append("|", style=_S_BORDER)
        for i, name in enumerate(col_names):
            text.append(f" {name:<{col_widths[i]}} ", style=_S_HEADER)
            text.append("|", style=_S_BORDER)
        text.append("\n")
        text.append(border + "\n", style=_S_BORDER)

        # Data rows
        for row_idx, row in enumerate(rows):
            text.append("|", style=_S_BORDER)
            for i, val in enumerate(row):
                w = col_widths[i] if i < len(col_widths) else len(cell_strings[row_idx][i])
                cell_text = _styled_cell(val)
                # Pad to column width
                padding = w - len(cell_strings[row_idx][i])
                text.append(" ")
                text.append_text(cell_text)
                if padding > 0:
                    text.append(" " * padding)
                text.append(" ", style=_S_BORDER)
                text.append("|", style=_S_BORDER)
            text.append("\n")
        text.append(border, style=_S_BORDER)
    else:
        # Simple format
        hdr = "  ".join(
            f"{name:<{col_widths[i]}}" for i, name in enumerate(col_names)
        )
        text.append(hdr + "\n", style=_S_HEADER)
        sep = "  ".join("-" * w for w in col_widths)
        text.append(sep + "\n", style=_S_BORDER)

        for row_idx, row in enumerate(rows):
            for i, val in enumerate(row):
                w = col_widths[i] if i < len(col_widths) else len(cell_strings[row_idx][i])
                cell_text = _styled_cell(val)
                padding = w - len(cell_strings[row_idx][i])
                text.append_text(cell_text)
                if padding > 0:
                    text.append(" " * padding)
                if i < len(row) - 1:
                    text.append("  ")
            text.append("\n")

    return text


def _build_vertical_text(col_names: list[str], rows: list[Any]) -> Text:
    """Build colored Rich Text for vertical (\\G) output."""
    max_name_len = max(len(name) for name in col_names)
    text = Text()

    for row_num, row in enumerate(rows, 1):
        text.append(
            f"{'*' * 27} {row_num}. row {'*' * 27}\n", style=_S_BORDER
        )
        for i, val in enumerate(row):
            name = col_names[i] if i < len(col_names) else f"col{i}"
            text.append(f"{name:>{max_name_len}}: ", style=_S_HEADER)
            cell = _styled_cell(val)
            text.append_text(cell)
            text.append("\n")
        text.append("\n")

    return text


def _build_table_plain(
    col_names: list[str], rows: list[Any], fmt: str
) -> list[str]:
    """Build plain text table for log file (no colors)."""
    col_widths = [len(name) for name in col_names]
    str_rows: list[list[str]] = []
    for row in rows:
        str_row = [_format_cell(val) for val in row]
        for i, s in enumerate(str_row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(s))
        str_rows.append(str_row)

    lines: list[str] = []
    if fmt == "mysql":
        border = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        hdr = "|" + "|".join(
            f" {name:<{col_widths[i]}} " for i, name in enumerate(col_names)
        ) + "|"
        lines.append(border)
        lines.append(hdr)
        lines.append(border)
        for str_row in str_rows:
            row_line = "|" + "|".join(
                f" {val:<{col_widths[i]}} "
                if i < len(col_widths) else f" {val} "
                for i, val in enumerate(str_row)
            ) + "|"
            lines.append(row_line)
        lines.append(border)
    else:
        hdr = "  ".join(f"{name:<{col_widths[i]}}" for i, name in enumerate(col_names))
        sep = "  ".join("-" * w for w in col_widths)
        lines.append(hdr)
        lines.append(sep)
        for str_row in str_rows:
            row_line = "  ".join(
                f"{val:<{col_widths[i]}}" if i < len(col_widths) else val
                for i, val in enumerate(str_row)
            )
            lines.append(row_line)
    return lines


def _build_vertical_plain(col_names: list[str], rows: list[Any]) -> list[str]:
    """Build plain text vertical output for log file."""
    max_name_len = max(len(name) for name in col_names)
    lines: list[str] = []
    for row_num, row in enumerate(rows, 1):
        lines.append(f"{'*' * 27} {row_num}. row {'*' * 27}")
        for i, val in enumerate(row):
            name = col_names[i] if i < len(col_names) else f"col{i}"
            lines.append(f"{name:>{max_name_len}}: {_format_cell(val)}")
        lines.append("")
    return lines


class _FilePromptScreen(Screen[str]):
    """Modal file browser for selecting or entering file paths."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    _FilePromptScreen {
        align: center middle;
        background: $background 80%;
    }

    #file-dialog {
        width: 80;
        height: 24;
        border: solid $accent;
        padding: 1 2;
        background: $surface;
    }

    #file-tree {
        height: 1fr;
        margin-bottom: 1;
        border: solid $panel-darken-1;
    }

    #file-path-input {
        width: 100%;
    }
    """

    def __init__(self, prompt: str, callback: Any, start_dir: str = "~") -> None:
        super().__init__()
        self._prompt = prompt
        self._callback = callback
        self._start_dir = start_dir

    def compose(self) -> ComposeResult:
        from textual.widgets import DirectoryTree

        with Vertical(id="file-dialog"):
            yield Static(self._prompt)
            yield DirectoryTree(Path(self._start_dir).expanduser(), id="file-tree")
            yield Input(
                placeholder="Enter file path or select above...",
                id="file-path-input",
            )

    def on_mount(self) -> None:
        """Focus the input."""
        self.query_one("#file-path-input", Input).focus()

    def on_directory_tree_file_selected(
        self, event: Any
    ) -> None:
        """When a file is selected in the tree, put its path in the input."""
        inp = self.query_one("#file-path-input", Input)
        inp.value = str(event.path)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the input field."""
        path = event.value.strip()
        self.dismiss(path)
        self._callback(path)

    def action_cancel(self) -> None:
        """Cancel without action."""
        self.dismiss("")
