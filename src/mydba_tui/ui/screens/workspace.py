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
from mydba_tui.ui.widgets.sql_editor import SQLEditor

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
            "shift+f7",
            "explain_json",
            "Explain JSON",
            key_display="⇧F7",
            priority=True,
        ),
        Binding(
            "f8",
            "explain_analyze",
            "Analyze",
            key_display="F8",
            priority=True,
        ),
        Binding(
            "ctrl+s",
            "save_file",
            "Save SQL",
            key_display="^S",
            priority=True,
        ),
        Binding(
            "ctrl+o",
            "load_file",
            "Open SQL",
            key_display="^O",
            priority=True,
        ),
        Binding(
            "ctrl+l",
            "clear_results",
            "Clear",
            key_display="^L",
            priority=True,
        ),
        Binding(
            "ctrl+e",
            "export_results",
            "Export",
            key_display="^E",
            priority=True,
        ),
        Binding(
            "ctrl+shift+e",
            "direct_export",
            "Direct Export",
            key_display="^⇧E",
            priority=True,
        ),
        Binding(
            "ctrl+r",
            "cycle_row_limit",
            "Row Limit",
            key_display="^R",
            priority=True,
        ),
        Binding(
            "ctrl+shift+s",
            "save_log",
            "Save Log",
            key_display="^⇧S",
            priority=True,
        ),
        Binding(
            "ctrl+shift+f",
            "format_sql",
            "Format",
            key_display="^⇧F",
            priority=True,
        ),
        Binding(
            "f6",
            "switch_focus",
            "Switch Panel",
            key_display="F6",
            priority=True,
        ),
        Binding(
            "ctrl+shift+x",
            "reconnect",
            "Reconnect",
            key_display="^⇧X",
            priority=True,
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
            yield SQLEditor(id="sql-editor")
            yield ScrollableContainer(
                Static(
                    "[dim]Press F5 to execute SQL. F7 for EXPLAIN. F8 for EXPLAIN ANALYZE.[/dim]",
                    classes="result-info",
                ),
                id="results-panel",
            )

        yield Footer()

    def on_mount(self) -> None:
        """Focus the editor on mount and apply custom SQL theme."""
        from mydba_tui.ui.sql_theme import SQL_THEME, SQL_THEME_NAME

        self._sync_status_bar()
        sql_editor = self.query_one("#sql-editor", SQLEditor)
        editor = sql_editor.editor
        editor.register_theme(SQL_THEME)
        editor.theme = SQL_THEME_NAME
        editor.focus()

    def on_screen_resume(self) -> None:
        """Update status bar when returning to this screen."""
        self._sync_status_bar()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Trigger autocomplete on typing in the SQL editor."""
        if event.text_area.id != "sql-editor-inner":
            return
        # Skip if we just accepted a completion (prevents re-trigger loop)
        sql_editor = self.query_one("#sql-editor", SQLEditor)
        if sql_editor._skip_next_trigger:
            sql_editor._skip_next_trigger = False
            return
        self._trigger_autocomplete()

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
        self._session_log_path.write_text("\n".join(header_lines) + "\n", encoding="utf-8")

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
        entry = f"-- [{ts}] ({_format_duration(duration)})\n{sql};\n\n{result_text}\n\n"
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
            self._session_log_path = None

    def reset_for_new_connection(self) -> None:
        """Reset workspace state when switching to a different connection.

        Called when the active connection endpoint changes (a genuine profile
        switch, not a same-host reconnect). Rotates the session log and clears
        the editor and results so the new connection starts clean. A same-host
        reconnect deliberately does not call this, preserving the work session.
        """
        # Rotate the session log (delete unsaved, force a fresh one next time).
        self._cleanup_session_log()
        self._session_saved = False

        # Clear the editor.
        try:
            editor = self.query_one("#sql-editor", SQLEditor).editor
            editor.clear()
        except Exception:
            pass

        # Clear results and status.
        try:
            panel = self.query_one("#results-panel", ScrollableContainer)
            panel.remove_children()
            panel.mount(
                Static(
                    "[dim]Press F5 to execute SQL. F7 for EXPLAIN. F8 for EXPLAIN ANALYZE.[/dim]",
                    classes="result-info",
                )
            )
        except Exception:
            pass
        self._result_count = 0
        self._results_store.clear()
        self._file_path = ""
        if self.is_mounted:
            self._sync_status_bar()

    def reload_after_reconnect(self) -> None:
        """Refresh workspace state after a reconnect to the same endpoint.

        The session log and editor are preserved; only the status bar is
        re-synced (metadata caches are rebuilt lazily on next autocomplete).
        """
        if self.is_mounted:
            self._sync_status_bar()

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
        editor = self.query_one("#sql-editor", SQLEditor).editor
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
            self.app.call_from_thread(self._append_error, "Not connected to a database.")
            return

        # Split into individual statements (handles ; and \G)
        statements = self._split_statements(sql)

        for stmt, vertical in statements:
            stmt = stmt.strip()
            if not stmt:
                continue

            self.app.call_from_thread(self._update_status, f"Executing: {stmt[:60]}...")

            start = _time.perf_counter()
            try:
                cursor = conn_result.connection.cursor(buffered=True)
                cursor.execute(stmt)

                duration = _time.perf_counter() - start
                log_sql(stmt, duration, "workspace")

                if cursor.description:
                    col_names = [desc[0] for desc in cursor.description]

                    self.app.call_from_thread(self._update_status, "Fetching results...")

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
                    self.app.call_from_thread(self._append_info, stmt, summary, duration)
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
        panel.mount(Static(f"[bold yellow]⏳ {message}[/bold yellow]", id="exec-status"))
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
        summary = f"{row_label} ({_format_duration(duration)})"

        # Header (with markup): timestamp + SQL
        header_lines: list[str] = []
        header_lines.append(f"[bold]── {ts} ──[/bold]")
        header_lines.append(f"[dim]{rich_escape(sql.rstrip(';'))};[/dim]")

        panel.mount(Static("\n".join(header_lines), classes="result-block"))

        # Data (colored Rich Text)
        data_lines: list[str] = []
        if not rows:
            panel.mount(Static("[dim]Empty set.[/dim]", classes="result-block"))
        elif vertical:
            # Vertical output (\G style) — colored
            data_text = _build_vertical_text(col_names, rows)
            data_widget = Static(data_text, classes="result-data")
            panel.mount(data_widget)
            # Plain text for log
            data_lines = _build_vertical_plain(col_names, rows)
        else:
            # Tabular output — colored
            result_format = getattr(getattr(self.app, "settings", None), "result_format", "mysql")
            data_text = _build_table_text(col_names, rows, result_format)
            data_widget = Static(data_text, classes="result-data")
            data_widget.styles.width = "auto"
            panel.mount(data_widget)
            # Plain text for log
            data_lines = _build_table_plain(col_names, rows, result_format)

        # Summary AFTER results
        panel.mount(Static(f"[bold]{summary}[/bold]\n", classes="result-block"))

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
            f"[dim]{rich_escape(sql.rstrip(';'))};[/dim]\n\n"
            f"[bold]{message} ({_format_duration(duration)})[/bold]\n"
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
            lines.append(f"[dim]{rich_escape(sql.rstrip(';'))};[/dim]")
            lines.append("")
        lines.append(f"[bold red]ERROR:[/bold red] [red]{rich_escape(error)}[/red]")
        lines.append("")

        panel.mount(Static("\n".join(lines), classes="result-block"))
        panel.scroll_end()

    # --- File Operations ---

    def action_save_file(self) -> None:
        """Save editor contents to a file."""
        editor = self.query_one("#sql-editor", SQLEditor).editor
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
        editor = self.query_one("#sql-editor", SQLEditor).editor
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
            editor = self.query_one("#sql-editor", SQLEditor).editor
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
            self.query_one("#sql-editor", SQLEditor).editor.focus()
        else:
            self.query_one("#results-panel", ScrollableContainer).focus()

    def action_clear_results(self) -> None:
        """Clear all results from the results panel."""
        panel = self.query_one("#results-panel", ScrollableContainer)
        panel.remove_children()
        panel.mount(Static("[dim]Results cleared.[/dim]", classes="result-info"))
        self._result_count = 0
        self._results_store.clear()

    def action_export_results(self) -> None:
        """Export the last result set to a file."""
        if not self._results_store:
            self.notify("No results to export.", severity="warning")
            return

        # Show format selection
        self.app.push_screen(
            _ExportFormatScreen(self._do_export),
        )

    def _do_export(self, fmt: str) -> None:
        """Handle format selection — prompt for file path."""
        if not fmt:
            return
        self._export_format = fmt
        self.app.push_screen(
            _FilePromptScreen(
                f"Export as {fmt.upper()} — save to:",
                self._do_export_to_file,
            ),
        )

    def _do_export_to_file(self, path_str: str) -> None:
        """Perform the actual export to the given path."""
        if not path_str:
            return

        from mydba_tui.exporters import EXPORTERS, export_result_set

        fmt = getattr(self, "_export_format", "csv")
        exporter_cls = EXPORTERS.get(fmt)
        if not exporter_cls:
            self.notify(f"Unknown format: {fmt}", severity="error")
            return

        path = Path(path_str)

        # Get the last result set
        col_names, rows = self._results_store[-1]

        try:
            exporter = exporter_cls()
            count = export_result_set(col_names, rows, path, exporter)
            self.notify(f"Exported {count:,} rows to {path}")
        except FileExistsError:
            self.notify(
                f"File already exists: {path}. Choose another name.",
                severity="error",
            )
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")

    # --- Direct Export (stream to file) ---

    def action_direct_export(self) -> None:
        """Execute query and stream results directly to a file."""
        sql = self._get_sql_to_execute()
        if not sql.strip():
            self.notify("No SQL to export.", severity="warning")
            return
        self._ensure_session_log()
        self._direct_export_sql = sql
        self.app.push_screen(
            _ExportFormatScreen(self._do_direct_export_format),
        )

    def _do_direct_export_format(self, fmt: str) -> None:
        """Handle format selection for direct export."""
        if not fmt:
            return
        self._direct_export_format = fmt
        self.app.push_screen(
            _FilePromptScreen(
                f"Direct export as {fmt.upper()} — save to:",
                self._do_direct_export_to_file,
            ),
        )

    def _do_direct_export_to_file(self, path_str: str) -> None:
        """Execute and stream results directly to file."""
        if not path_str:
            return

        path = Path(path_str)
        if path.exists():
            self.notify(
                f"File already exists: {path}. Choose another name.",
                severity="error",
            )
            return

        sql = getattr(self, "_direct_export_sql", "")
        fmt = getattr(self, "_direct_export_format", "csv")

        self._append_status("Direct export: executing...")
        self.run_worker(
            lambda: self._direct_export_thread(sql, path, fmt),
            name="direct_export",
            exclusive=True,
            thread=True,
        )

    def _direct_export_thread(self, sql: str, path: Path, fmt: str) -> None:
        """Execute query and stream rows to file (runs in thread)."""
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.exporters import EXPORTERS
        from mydba_tui.logging import log_sql

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            self.app.call_from_thread(self._remove_status)
            self.app.call_from_thread(self._append_error, "Not connected to a database.")
            return

        exporter_cls = EXPORTERS.get(fmt)
        if not exporter_cls:
            self.app.call_from_thread(self._remove_status)
            self.app.call_from_thread(self._append_error, f"Unknown format: {fmt}")
            return

        start = _time.perf_counter()
        try:
            # Use unbuffered cursor for streaming
            cursor = conn_result.connection.cursor(buffered=False)
            cursor.execute(sql)

            duration_exec = _time.perf_counter() - start
            log_sql(sql, duration_exec, "workspace.direct_export")

            if not cursor.description:
                cursor.close()
                self.app.call_from_thread(self._remove_status)
                self.app.call_from_thread(
                    self._append_error,
                    "Query did not return a result set.",
                    sql,
                )
                return

            col_names = [desc[0] for desc in cursor.description]
            exporter = exporter_cls()

            path.parent.mkdir(parents=True, exist_ok=True)
            row_count = 0

            with path.open("w", encoding="utf-8", newline="") as f:
                exporter.initialize(f, col_names)

                for row in cursor:  # type: ignore[union-attr]
                    exporter.write_row(row)
                    row_count += 1
                    if row_count % 10000 == 0:
                        self.app.call_from_thread(
                            self._update_status,
                            f"Exporting: {row_count:,} rows...",
                        )

                exporter.finalize()

            cursor.close()
            duration_total = _time.perf_counter() - start

            self.app.call_from_thread(self._remove_status)

            from rich.markup import escape as rich_escape

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = (
                f"[bold]── {ts} ──[/bold]\n"
                f"[dim]{rich_escape(sql.rstrip(';'))};[/dim]\n\n"
                f"[bold]Direct export complete:[/bold]\n"
                f"  Rows: {row_count:,}\n"
                f"  Format: {exporter_cls.name}\n"
                f"  File: {path}\n"
                f"  Duration: {_format_duration(duration_total)}\n"
            )
            self.app.call_from_thread(self._append_direct_export_result, msg)

            # Log to session
            log_text = (
                f"Direct export: {row_count:,} rows to {path}\n"
                f"Format: {exporter_cls.name}\n"
                f"Duration: {_format_duration(duration_total)}"
            )
            self._log_to_session(sql, log_text, duration_total)

        except Exception as e:
            self.app.call_from_thread(self._remove_status)
            self.app.call_from_thread(self._append_error, str(e), sql)

    def _append_direct_export_result(self, msg: str) -> None:
        """Show direct export result in the results panel."""
        panel = self.query_one("#results-panel", ScrollableContainer)
        panel.mount(Static(msg, classes="result-block"))
        panel.scroll_end()

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

    def action_format_sql(self) -> None:
        """Format SQL in the editor using sqlglot (MySQL dialect).

        Formats selected text if any, otherwise formats entire editor contents.
        Applies configurable post-processing rules from settings.
        """
        import sqlglot

        editor = self.query_one("#sql-editor", SQLEditor).editor
        selected = editor.selected_text
        has_selection = bool(selected and selected.strip())
        sql = selected if has_selection else editor.text

        if not sql.strip():
            return

        try:
            formatted = sqlglot.transpile(sql.strip(), read="mysql", write="mysql", pretty=True)
            result = ";\n\n".join(formatted)
            if not result.endswith(";"):
                result += ";"

            # Apply post-processing rules
            result = _apply_format_rules(result, self.app)

            if has_selection:
                # Replace only the selected text
                start, end = editor.selection
                if start > end:
                    start, end = end, start
                editor.replace(result, start, end)
            else:
                # Replace all content
                editor.clear()
                editor.insert(result)

            self.notify("SQL formatted.")
        except Exception as e:
            self.notify(f"Format failed: {e}", severity="error")

    def _trigger_autocomplete(self) -> None:
        """Show SQL autocomplete suggestions at the cursor."""
        from mydba_tui.ui.mysql_autocomplete import (
            get_completions,
            get_completions_after_dot,
        )

        sql_editor = self.query_one("#sql-editor", SQLEditor)
        editor = sql_editor.editor

        # Get the current word being typed
        cursor_row, cursor_col = editor.cursor_location
        line = str(editor.get_line(cursor_row))
        text_before = line[:cursor_col]

        # Detect dot completion (schema.object or table.column)
        dot_match = _DOT_PATTERN.search(text_before)
        prefix = ""
        if dot_match:
            name_before_dot = dot_match.group(1)
            prefix_after_dot = dot_match.group(2) or ""

            # First check if it's a schema name → suggest objects from that schema
            schema_objects = self._get_schema_objects_cache()
            schemas = (schema_objects or {}).get("schemas", [])
            if name_before_dot in schemas or name_before_dot.lower() in [
                s.lower() for s in schemas
            ]:
                # It's schema.object completion
                objects = self._get_schema_objects_for(name_before_dot)
                upper_prefix = prefix_after_dot.upper()
                from mydba_tui.ui.mysql_autocomplete import (
                    CompletionItem,
                    CompletionKind,
                )

                items = [
                    CompletionItem(text=obj, kind=CompletionKind.TABLE)
                    for obj in objects
                    if obj.upper().startswith(upper_prefix)
                ][:50]
            else:
                # It's table.column completion
                table_columns = self._get_table_columns_cache()
                items = get_completions_after_dot(name_before_dot, table_columns, prefix_after_dot)
        else:
            # Get word prefix — need at least 2 chars to trigger
            prefix = _get_word_at_cursor(text_before)
            if not prefix or len(prefix) < 2:
                sql_editor.hide_completions()
                return

            # Get schema objects from app
            schema_objects = self._get_schema_objects_cache()
            table_columns = self._get_table_columns_cache()
            current_table = self._detect_current_table(editor.text, cursor_row)
            # Detect if we're at the start of a statement
            at_start = _is_statement_start(text_before)
            items = get_completions(
                prefix,
                schema_objects,
                table_columns,
                current_table,
                at_statement_start=at_start,
            )

        if not items:
            sql_editor.hide_completions()
            return

        # If the typed word exactly matches the only suggestion, hide
        typed = (dot_match.group(2) or "") if dot_match else prefix
        if len(items) == 1 and items[0].text.upper() == typed.upper():
            sql_editor.hide_completions()
            return

        # Show completions
        display_items = [item.display for item in items]
        insert_texts = [item.text for item in items]
        kinds = [item.kind.value for item in items]
        sql_editor.show_completions(display_items, insert_texts, kinds)

    def _get_schema_objects_cache(self) -> dict[str, list[str]] | None:
        """Get schema objects for autocomplete.

        Returns dict with keys:
            schemas: all schema names
            tables: tables in current schema
            views: views in current schema
            procedures: procedures in current schema
            functions: functions in current schema
        Also stores per-schema cache in app._schema_objects_map.
        """
        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None:
            return None

        existing = getattr(self.app, "_autocomplete_cache", None)
        if existing:
            return existing  # type: ignore[no-any-return]

        try:
            from mydba_tui.connection import ConnectionResult

            if not isinstance(conn_result, ConnectionResult):
                return None

            cursor = conn_result.connection.cursor(buffered=True)

            # Get all schema names
            cursor.execute("SELECT schema_name FROM information_schema.schemata")
            schemas = [str(r[0]) for r in cursor.fetchall()]  # type: ignore[index]

            # Get current database
            cursor.execute("SELECT DATABASE()")
            row = cursor.fetchone()
            current_db = str(row[0]) if row and row[0] else ""  # type: ignore[index]

            # Get tables/views in current db
            tables: list[str] = []
            views: list[str] = []
            if current_db:
                cursor.execute(
                    "SELECT table_name, table_type "
                    "FROM information_schema.tables "
                    f"WHERE table_schema = '{current_db}'"
                )
                for r in cursor.fetchall():
                    name = str(r[0])  # type: ignore[index]
                    if r[1] == "BASE TABLE":  # type: ignore[index]
                        tables.append(name)
                    else:
                        views.append(name)

            # Get procedures/functions in current db
            procs: list[str] = []
            funcs: list[str] = []
            if current_db:
                cursor.execute(
                    "SELECT routine_name, routine_type "
                    "FROM information_schema.routines "
                    f"WHERE routine_schema = '{current_db}'"
                )
                for r in cursor.fetchall():
                    name = str(r[0])  # type: ignore[index]
                    if r[1] == "PROCEDURE":  # type: ignore[index]
                        procs.append(name)
                    else:
                        funcs.append(name)

            cursor.close()

            cache: dict[str, list[str]] = {
                "schemas": schemas,
                "tables": tables,
                "views": views,
                "procedures": procs,
                "functions": funcs,
            }
            self.app._autocomplete_cache = cache  # type: ignore[attr-defined]
            self.app._autocomplete_current_db = current_db  # type: ignore[attr-defined]
            return cache
        except Exception:
            return None

    def _get_schema_objects_for(self, schema: str) -> list[str]:
        """Get objects (tables/views/routines) for a specific schema."""
        # Check per-schema cache
        schema_map = getattr(self.app, "_schema_objects_map", None)
        if schema_map and schema in schema_map:
            return schema_map[schema]  # type: ignore[no-any-return]

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None:
            return []

        try:
            from mydba_tui.connection import ConnectionResult

            if not isinstance(conn_result, ConnectionResult):
                return []

            cursor = conn_result.connection.cursor(buffered=True)
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = '{schema}' "
                "UNION "
                "SELECT routine_name FROM information_schema.routines "
                f"WHERE routine_schema = '{schema}'"
            )
            objects = [str(r[0]) for r in cursor.fetchall()]  # type: ignore[index]
            cursor.close()

            # Cache it
            if not schema_map:
                schema_map = {}
            schema_map[schema] = objects
            self.app._schema_objects_map = schema_map  # type: ignore[attr-defined]
            return objects
        except Exception:
            return []

    def _get_table_columns_cache(self) -> dict[str, list[str]] | None:
        """Get table→columns mapping from cached data."""
        return getattr(self.app, "_column_cache", None)

    def _detect_current_table(self, sql: str, cursor_row: int) -> str | None:
        """Try to detect the current table context from SQL near cursor."""
        # Simple heuristic: look for FROM/JOIN table_name near cursor
        lines = sql.split("\n")
        # Look backwards from cursor for FROM/JOIN
        for i in range(cursor_row, max(cursor_row - 10, -1), -1):
            if i < len(lines):
                line_upper = lines[i].upper()
                for kw in ("FROM ", "JOIN ", "UPDATE ", "INTO "):
                    pos = line_upper.find(kw)
                    if pos >= 0:
                        # Extract table name after keyword
                        after = lines[i][pos + len(kw) :].strip()
                        table = after.split()[0].strip("`") if after else ""
                        if table:
                            return table
        return None

    def action_go_back(self) -> None:
        """Exit workspace (or dismiss completions if visible)."""
        try:
            sql_editor = self.query_one("#sql-editor", SQLEditor)
            if sql_editor.popup.is_visible:
                sql_editor.hide_completions()
                return
        except Exception:
            pass
        # Don't delete session log — it persists across workspace visits
        self.app.pop_screen()

    def action_reconnect(self) -> None:
        """Reconnect to the current profile (preserves session log/editor)."""
        self.app.reconnect()  # type: ignore[attr-defined]

    def action_quit(self) -> None:
        """Exit the application."""
        self._cleanup_session_log()
        self.app.exit()


# --- Autocomplete helpers ---

_DOT_PATTERN = re.compile(r"`?(\w+)`?\.\s*`?(\w*)$")


def _get_word_at_cursor(text_before_cursor: str) -> str:
    """Extract the word being typed at the cursor position."""
    i = len(text_before_cursor) - 1
    while i >= 0 and (text_before_cursor[i].isalnum() or text_before_cursor[i] == "_"):
        i -= 1
    return text_before_cursor[i + 1 :]


def _format_duration(seconds: float) -> str:
    """Format a duration in human-readable form.

    < 60s: show with millisecond precision (e.g., "1.234s")
    >= 60s and < 1h: show as "Xm Ys" (e.g., "2m 34s")
    >= 1h: show as "Xh Ym Zs" (e.g., "1h 23m 45s")
    """
    if seconds < 60:
        return f"{seconds:.3f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m {secs}s"


def _is_statement_start(text_before_cursor: str) -> bool:
    """Check if cursor is at the start of a SQL statement.

    Returns True if there are no previous keywords on the current line
    (just whitespace or nothing before the prefix).
    """
    # Strip the current word being typed
    stripped = text_before_cursor.rstrip()
    # Remove trailing word chars (the prefix being typed)
    i = len(stripped) - 1
    while i >= 0 and (stripped[i].isalnum() or stripped[i] == "_"):
        i -= 1
    before_word = stripped[: i + 1].strip()
    # At statement start if nothing meaningful before, or after ; or blank line
    if not before_word:
        return True
    if before_word.endswith(";"):
        return True
    return False


def _apply_format_rules(sql: str, app: Any) -> str:
    """Apply configurable post-processing rules to formatted SQL.

    Rules are read from app.settings.format_rules (dict) if available.
    Supported rules:
        select_star_inline (bool): Keep SELECT * on one line. Default: true.
        keyword_case (str): 'upper', 'lower', 'preserve'. Default: 'upper'.
        indent_width (int): Spaces per indent. Default: 2 (sqlglot default).
    """
    rules = getattr(getattr(app, "settings", None), "format_rules", None)
    if rules is None:
        rules = {}

    # Rule: select_star_inline (default: true)
    if rules.get("select_star_inline", True):
        sql = re.sub(r"SELECT\s*\n\s+\*", "SELECT *", sql, flags=re.IGNORECASE)

    # Rule: keyword_case
    case = rules.get("keyword_case", "upper")
    if case == "lower":
        from mydba_tui.ui.mysql_highlight import _FLOW_KEYWORDS, _KEYWORDS

        all_kw = _KEYWORDS | _FLOW_KEYWORDS
        for kw in sorted(all_kw, key=len, reverse=True):
            sql = re.sub(rf"\b{kw}\b", kw.lower(), sql, flags=re.IGNORECASE)

    # Rule: indent_width (post-process indentation)
    indent_width = rules.get("indent_width", 2)
    if indent_width != 2:
        lines = sql.split("\n")
        adjusted = []
        for line in lines:
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)
            # Convert from 2-space to target width
            indent_level = current_indent // 2
            new_indent = " " * (indent_level * indent_width)
            adjusted.append(new_indent + stripped)
        sql = "\n".join(adjusted)

    return sql


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
    if (stripped[0] == "{" and stripped[-1] == "}") or (stripped[0] == "[" and stripped[-1] == "]"):
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


def _build_table_text(col_names: list[str], rows: list[Any], fmt: str) -> Text:
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
        hdr = "  ".join(f"{name:<{col_widths[i]}}" for i, name in enumerate(col_names))
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
        text.append(f"{'*' * 27} {row_num}. row {'*' * 27}\n", style=_S_BORDER)
        for i, val in enumerate(row):
            name = col_names[i] if i < len(col_names) else f"col{i}"
            text.append(f"{name:>{max_name_len}}: ", style=_S_HEADER)
            cell = _styled_cell(val)
            text.append_text(cell)
            text.append("\n")
        text.append("\n")

    return text


def _build_table_plain(col_names: list[str], rows: list[Any], fmt: str) -> list[str]:
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
        hdr = "|" + "|".join(f" {name:<{col_widths[i]}} " for i, name in enumerate(col_names)) + "|"
        lines.append(border)
        lines.append(hdr)
        lines.append(border)
        for str_row in str_rows:
            row_line = (
                "|"
                + "|".join(
                    f" {val:<{col_widths[i]}} " if i < len(col_widths) else f" {val} "
                    for i, val in enumerate(str_row)
                )
                + "|"
            )
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


class _ExportFormatScreen(Screen[str]):
    """Modal dialog for selecting export format."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    _ExportFormatScreen {
        align: center middle;
        background: $background 80%;
    }

    #export-format-container {
        width: 40;
        height: auto;
        border: solid $accent;
        padding: 1 2;
        background: $surface;
    }

    .format-option {
        padding: 0 1;
        margin-bottom: 0;
    }

    .format-option:hover {
        background: $accent;
    }
    """

    def __init__(self, callback: Any) -> None:
        super().__init__()
        self._callback = callback

    def compose(self) -> ComposeResult:
        from textual.widgets import OptionList

        from mydba_tui.exporters import EXPORTERS

        with Vertical(id="export-format-container"):
            yield Static("[bold]Export format:[/bold]\n")
            options = [EXPORTERS[key].name for key in sorted(EXPORTERS.keys())]
            yield OptionList(*options, id="format-list")

    def on_mount(self) -> None:
        """Focus the list."""
        from textual.widgets import OptionList

        self.query_one("#format-list", OptionList).focus()

    def on_option_list_option_selected(self, event: Any) -> None:
        """Handle format selection."""
        from mydba_tui.exporters import EXPORTERS

        keys = sorted(EXPORTERS.keys())
        idx = event.option_index
        if 0 <= idx < len(keys):
            self.dismiss(keys[idx])
            self._callback(keys[idx])

    def action_cancel(self) -> None:
        """Cancel export."""
        self.dismiss("")


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
        self._current_dir: Path = Path(start_dir).expanduser()

    def compose(self) -> ComposeResult:
        from textual.widgets import DirectoryTree

        with Vertical(id="file-dialog"):
            yield Static(self._prompt)
            yield DirectoryTree(self._current_dir, id="file-tree")
            yield Input(
                placeholder="Enter file path or select above...",
                id="file-path-input",
                value=str(self._current_dir) + "/",
            )

    def on_mount(self) -> None:
        """Focus the input."""
        self.query_one("#file-path-input", Input).focus()

    def on_directory_tree_file_selected(self, event: Any) -> None:
        """When a file is selected in the tree, put its full path in the input."""
        inp = self.query_one("#file-path-input", Input)
        inp.value = str(event.path)

    def on_directory_tree_directory_selected(self, event: Any) -> None:
        """When a directory is selected, update the input with the directory path."""
        self._current_dir = Path(event.path)
        inp = self.query_one("#file-path-input", Input)
        # Only update if user hasn't typed a full path
        current_val = inp.value.strip()
        if not current_val or current_val.endswith("/"):
            inp.value = str(self._current_dir) + "/"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the input field."""
        path = event.value.strip()
        if not path:
            return

        # If path is not absolute, prepend the current directory
        p = Path(path)
        if not p.is_absolute():
            p = self._current_dir / p

        result = str(p)
        self.dismiss(result)
        self._callback(result)

    def action_cancel(self) -> None:
        """Cancel without action."""
        self.dismiss("")
