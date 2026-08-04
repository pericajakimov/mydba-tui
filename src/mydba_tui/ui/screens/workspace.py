"""
SQL Workspace screen.

Provides the interactive SQL editor and execution workspace.
Results are displayed with timestamp and SQL for each block.
A session log file is maintained in ~/.config/mydba/logs/sessions/
and auto-deleted on clean exit unless explicitly saved.
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, TextArea

from mydba_tui.ui.widgets import StatusBar

_SESSIONS_DIR = Path.home() / ".config" / "mydba" / "logs" / "sessions"


class WorkspaceScreen(Screen[None]):
    """SQL Workspace — interactive SQL editor and results viewer."""

    BINDINGS = [
        Binding("f5", "execute", "Execute", key_display="F5"),
        Binding("f7", "explain", "Explain", key_display="F7"),
        Binding("shift+f7", "explain_json", "Explain JSON", key_display="⇧F7"),
        Binding("f8", "explain_analyze", "Explain Analyze", key_display="F8"),
        Binding("ctrl+s", "save_file", "Save", key_display="^S"),
        Binding("ctrl+o", "load_file", "Open", key_display="^O"),
        Binding("ctrl+l", "clear_results", "Clear", key_display="^L"),
        Binding("f6", "switch_focus", "Switch Panel", key_display="F6"),
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
    }

    .result-block {
        padding: 0 1;
        margin-bottom: 1;
    }

    .result-error {
        color: $error;
        padding: 0 1;
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

    def compose(self) -> ComposeResult:
        """Build the workspace layout."""
        yield Header()
        yield StatusBar(id="status-bar")

        with Vertical(id="workspace-layout"):
            yield TextArea(
                "",
                language="sql",
                theme="monokai",
                show_line_numbers=True,
                id="sql-editor",
            )
            yield VerticalScroll(
                Static(
                    "[dim]Press F5 to execute SQL. "
                    "F7 for EXPLAIN. F8 for EXPLAIN ANALYZE.[/dim]",
                    classes="result-info",
                ),
                id="results-panel",
            )

        yield Footer()

    def on_mount(self) -> None:
        """Focus the editor on mount."""
        self._sync_status_bar()
        self.query_one("#sql-editor", TextArea).focus()

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
            header_lines.append(f"# Connection: {conn_status}")

        header_lines.append("")
        self._session_log_path.write_text(
            "\n".join(header_lines) + "\n", encoding="utf-8"
        )

    def _log_to_session(
        self, sql: str, result_summary: str, duration: float
    ) -> None:
        """Append an execution record to the session log."""
        if self._session_log_path is None:
            return

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"-- [{ts}] ({duration:.3f}s)\n"
            f"{sql};\n"
            f"-- {result_summary}\n\n"
        )
        with open(self._session_log_path, "a", encoding="utf-8") as f:
            f.write(entry)

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
        self._execute_sql(sql)

    def action_explain(self) -> None:
        """Run EXPLAIN on the selected text or editor contents."""
        sql = self._get_sql_to_execute()
        if not sql.strip():
            return
        self._ensure_session_log()
        self._execute_sql(f"EXPLAIN {sql.strip().rstrip(';')}")

    def action_explain_json(self) -> None:
        """Run EXPLAIN FORMAT=JSON on the selected text or editor contents."""
        sql = self._get_sql_to_execute()
        if not sql.strip():
            return
        self._ensure_session_log()
        self._execute_sql(f"EXPLAIN FORMAT=JSON {sql.strip().rstrip(';')}")

    def action_explain_analyze(self) -> None:
        """Run EXPLAIN ANALYZE on the selected text or editor contents."""
        sql = self._get_sql_to_execute()
        if not sql.strip():
            return
        self._ensure_session_log()
        self._execute_sql(f"EXPLAIN ANALYZE {sql.strip().rstrip(';')}")

    def _get_sql_to_execute(self) -> str:
        """Get SQL text: selected text if any, otherwise full editor contents."""
        editor = self.query_one("#sql-editor", TextArea)
        selected = editor.selected_text
        if selected and selected.strip():
            return selected
        return editor.text

    def _execute_sql(self, sql: str) -> None:
        """Execute one or more SQL statements and display results."""
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.logging import log_sql

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self._append_error("Not connected to a database.")
            return

        # Split into individual statements (handles ; and \G)
        statements = self._split_statements(sql)

        for stmt, vertical in statements:
            stmt = stmt.strip()
            if not stmt:
                continue

            start = time.perf_counter()
            try:
                cursor = conn_result.connection.cursor(buffered=True)
                cursor.execute(stmt)

                duration = time.perf_counter() - start
                log_sql(stmt, duration, "workspace")

                if cursor.description:
                    # Result set — fetch and display
                    col_names = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    self._append_result_set(
                        stmt, col_names, rows, duration, vertical=vertical
                    )
                else:
                    # DML/DDL — show affected rows
                    affected = cursor.rowcount
                    summary = f"{affected} row(s) affected"
                    self._append_info(stmt, summary, duration)
                    self._log_to_session(stmt, summary, duration)

                cursor.close()

            except Exception as e:
                duration = time.perf_counter() - start
                log_sql(stmt, duration, "workspace.error")
                self._append_error(str(e), stmt)
                self._log_to_session(stmt, f"ERROR: {e}", duration)

    def _split_statements(self, sql: str) -> list[tuple[str, bool]]:
        """Split SQL text into individual statements.

        Handles both ; and \\G as terminators.
        Returns list of (statement, vertical_output) tuples.
        """
        import re

        results: list[tuple[str, bool]] = []
        # Split on ; or \G (keeping track of which terminator was used)
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

    # --- Result Display ---

    def _append_result_set(
        self,
        sql: str,
        col_names: list[str],
        rows: list[Any],
        duration: float,
        vertical: bool = False,
    ) -> None:
        """Append a result set to the results panel."""
        self._result_count += 1
        panel = self.query_one("#results-panel", VerticalScroll)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_label = f"{len(rows)} row{'s' if len(rows) != 1 else ''}"
        summary = f"{row_label} ({duration:.3f}s)"

        # Build the block
        lines: list[str] = []
        lines.append(f"[bold]── {ts} ──[/bold]")
        lines.append(f"[dim]{sql};[/dim]")
        lines.append("")
        lines.append(f"[bold]{summary}[/bold]")

        if not rows:
            lines.append("[dim]Empty set.[/dim]")
        elif vertical:
            # Vertical output (\G style)
            max_name_len = max(len(name) for name in col_names)
            for row_num, row in enumerate(rows, 1):
                lines.append(
                    f"[bold]{'*' * 27} {row_num}. row {'*' * 27}[/bold]"
                )
                for i, val in enumerate(row):
                    name = col_names[i] if i < len(col_names) else f"col{i}"
                    if val is None:
                        val_str = "[dim]NULL[/dim]"
                    else:
                        val_str = str(val)
                    lines.append(f"{name:>{max_name_len}}: {val_str}")
        else:
            # Tabular output — no column width cap for horizontal scrolling
            col_widths = [len(name) for name in col_names]
            str_rows: list[list[str]] = []
            for row in rows:
                str_row = []
                for i, val in enumerate(row):
                    s = "NULL" if val is None else str(val)
                    if len(s) > 200:
                        s = s[:200] + "..."
                    str_row.append(s)
                    if i < len(col_widths):
                        col_widths[i] = max(col_widths[i], len(s))
                str_rows.append(str_row)

            # Column headers
            hdr = "  ".join(
                f"{name:<{col_widths[i]}}" for i, name in enumerate(col_names)
            )
            lines.append(f"[bold]{hdr}[/bold]")
            lines.append(
                "  ".join("─" * col_widths[i] for i in range(len(col_names)))
            )

            # Data rows
            for str_row in str_rows:
                parts = []
                for i, val in enumerate(str_row):
                    w = col_widths[i] if i < len(col_widths) else len(val)
                    if val == "NULL":
                        parts.append(f"[dim]{val:<{w}}[/dim]")
                    else:
                        parts.append(f"{val:<{w}}")
                lines.append("  ".join(parts))

        lines.append("")

        result_widget = Static("\n".join(lines), classes="result-block")
        result_widget.styles.overflow_x = "auto"
        panel.mount(result_widget)
        panel.scroll_end()

        # Log to session file
        self._log_to_session(sql, summary, duration)

    def _append_info(self, sql: str, message: str, duration: float) -> None:
        """Append an info message (DML result) to the results panel."""
        self._result_count += 1
        panel = self.query_one("#results-panel", VerticalScroll)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = (
            f"[bold]── {ts} ──[/bold]\n"
            f"[dim]{sql};[/dim]\n\n"
            f"[bold]{message} ({duration:.3f}s)[/bold]\n"
        )
        panel.mount(Static(content, classes="result-block"))
        panel.scroll_end()

    def _append_error(self, error: str, sql: str = "") -> None:
        """Append an error message to the results panel."""
        self._result_count += 1
        panel = self.query_one("#results-panel", VerticalScroll)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines: list[str] = [f"[bold]── {ts} ──[/bold]"]
        if sql:
            lines.append(f"[dim]{sql};[/dim]")
            lines.append("")
        lines.append(f"[bold red]ERROR:[/bold red] [red]{error}[/red]")
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
            self.query_one("#results-panel", VerticalScroll).focus()

    def action_clear_results(self) -> None:
        """Clear all results from the results panel."""
        panel = self.query_one("#results-panel", VerticalScroll)
        panel.remove_children()
        panel.mount(
            Static("[dim]Results cleared.[/dim]", classes="result-info")
        )
        self._result_count = 0

    def action_go_back(self) -> None:
        """Exit workspace and clean up session log if not saved."""
        self._cleanup_session_log()
        self.app.pop_screen()


class _FilePromptScreen(Screen[None]):
    """Simple modal screen for file path input."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    _FilePromptScreen {
        align: center middle;
    }

    #file-prompt-container {
        width: 60;
        height: auto;
        max-height: 7;
        border: solid $accent;
        padding: 1 2;
    }
    """

    def __init__(self, prompt: str, callback: Any) -> None:
        super().__init__()
        self._prompt = prompt
        self._callback = callback

    def compose(self) -> ComposeResult:
        with Vertical(id="file-prompt-container"):
            yield Static(self._prompt)
            yield TextArea("", id="file-input", show_line_numbers=False)

    def on_mount(self) -> None:
        """Focus the input."""
        self.query_one("#file-input", TextArea).focus()

    def key_enter(self) -> None:
        """Submit the file path."""
        path = self.query_one("#file-input", TextArea).text.strip()
        self.app.pop_screen()
        self._callback(path)

    def action_cancel(self) -> None:
        """Cancel without saving."""
        self.app.pop_screen()
