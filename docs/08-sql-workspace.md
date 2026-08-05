# SQL Workspace

## Purpose

The SQL Workspace is the primary environment for writing, executing, and reviewing SQL statements.

It is designed to preserve the familiar workflow of the traditional MySQL client while providing the editing capabilities expected from a modern SQL editor.

The SQL Workspace is intended to become the place where a DBA spends most of the interactive session.

---

# Design Goals

The SQL Workspace should:

- Feel familiar to MySQL users.
- Support efficient SQL editing.
- Preserve execution history.
- Display results in a readable format.
- Support large SQL scripts.
- Support multiple result sets.
- Integrate naturally with the Object Browser.
- Never hide executed SQL.

---

# Workspace Layout

The workspace consists of two primary areas.

```
+---------------------------------------------------------------+
| SQL Editor                                                    |
|                                                               |
| SELECT ...                                                    |
|                                                               |
+---------------------------------------------------------------+

| Result #1                                                     |
|                                                               |
| ...                                                           |
|                                                               |
+---------------------------------------------------------------+

| Result #2                                                     |
|                                                               |
| ...                                                           |
|                                                               |
+---------------------------------------------------------------+
```

The SQL editor remains at the top of the workspace.

Executed results are appended below the editor in chronological order.

---

# SQL Editor

The editor supports:

- Multi-line editing
- Syntax highlighting
- Standard text selection
- Copy and paste
- Undo and redo
- Scrolling
- Large SQL scripts

The editor should behave predictably and remain responsive for large scripts.

---

# SQL Execution

The SQL Workspace follows the execution model used by Microsoft SQL Server Management Studio (SSMS).

Execution is controlled by a single command.

If text is selected:

- Execute only the selected text.

If nothing is selected:

- Execute the entire editor contents.

This behavior should remain consistent throughout the application.

---

# Multiple Statements

The workspace supports execution of multiple SQL statements.

Statements are executed sequentially.

Results appear in the same order as execution.

---

# Multiple Result Sets

If a statement produces multiple result sets, they are displayed one after another.

Each result set has its own header.

Execution order is preserved.

---

# Result History

Results remain visible after execution.

Executing another query appends new results below the previous ones.

The workspace therefore acts as a session history.

Results remain available until:

- The application exits.
- The workspace is explicitly cleared.

---

# Query Cancellation

Long-running queries behave similarly to the MySQL client.

The user may interrupt execution using:

```
Ctrl+C
```

Query timeouts continue to be managed by MySQL session settings.

---

# SQL Files

The workspace allows loading SQL files from disk.

A simple file browser is used for file selection.

Loaded files replace the current editor contents.

---

# Syntax Highlighting

SQL displayed in the editor uses syntax highlighting.

The objective is to improve readability rather than introduce visual decoration.

Formatting should remain consistent with the rendering used throughout the application.

---

# SQL Formatting

The workspace provides automatic SQL formatting via `Ctrl+Shift+F`.

Behavior:

- If text is selected, only the selected text is formatted.
- If nothing is selected, the entire editor contents are formatted.

The formatter uses the MySQL dialect and produces:

- Uppercased keywords (configurable)
- Indented clauses (SELECT, FROM, WHERE, JOIN on separate lines)
- Proper alignment of subqueries and conditions
- One statement per block, separated by blank lines

Configurable rules in `settings.yaml`:

```yaml
format_rules:
  select_star_inline: true   # Keep SELECT * on one line
  keyword_case: upper        # upper, lower, or preserve
  indent_width: 2            # Spaces per indent level
```

The formatter is powered by sqlglot with MySQL dialect awareness.

---

# Result Rendering

Query results are displayed as formatted tables.

The renderer should support:

- Horizontal scrolling
- Vertical scrolling
- Wide result sets
- Large result sets

The presentation should remain readable even in narrow terminal windows.

---

# Vertical Output

The workspace supports vertical result display similar to the MySQL client's `\G` output.

Field names are right-aligned to the separator.

Example:

```
*************************** 1. row ***************************

             id: 123
           name: Example
         status: ACTIVE
     created_at: 2025-01-01 12:00:00
```

Vertical output is intended for:

- Wide rows
- JSON columns
- Inspection of individual records

---

# JSON Rendering

JSON values displayed in vertical output are automatically formatted.

Requirements:

- Proper indentation
- Syntax highlighting
- Consistent formatting
- Scrollable output

The renderer should make complex JSON documents easy to inspect without collapsing sections.

---

# EXPLAIN Support

Dedicated shortcuts provide quick access to query execution plans.

Supported execution modes:

- EXPLAIN (Tree)
- EXPLAIN FORMAT=JSON
- EXPLAIN ANALYZE

The SQL editor contents are used as the input.

The resulting plans are displayed using the standard rendering engine.

---

# Export

Query results may be exported after execution.

Supported formats:

- CSV
- TSV
- SQL INSERT
- JSONL

The export operation acts on the selected result set.

---

# Large Exports

Large exports are initiated before query execution.

Instead of displaying rows in the workspace, query output is redirected directly to the selected export file.

The workspace displays:

- Execution status
- Number of exported rows
- Execution time
- Destination file path

This avoids consuming unnecessary memory while exporting large datasets.

---

# SQL Logging

Every SQL statement executed from the workspace is recorded in the SQL log.

The SQL log contains only SQL statements together with execution timestamps and execution duration.

No Python logging messages appear in the SQL log.

---

# Autocomplete

SQL autocomplete triggers automatically while typing (after 2+ characters).

Completion sources:

- MySQL keywords (context-aware: only statement starters at the beginning)
- MySQL built-in functions (200+)
- MySQL data types
- Schema names (all schemas on the server)
- Tables, views, procedures, functions from the current database
- Objects from a specific schema after typing `schema_name.`

Behavior:

- Popup appears below the cursor (or above if near the editor bottom)
- Tab or Enter accepts the highlighted suggestion
- Up/Down arrows navigate the list
- Esc dismisses the popup
- Typing continues to filter results in real-time
- Space is added automatically after keywords (not after object names)

The metadata cache is built on first trigger and reused within the session.

---

# Session Lifetime

The SQL Workspace belongs to the current application session.

Its contents are not restored after reconnecting or restarting the application.

This behavior intentionally matches the workflow of the traditional MySQL client.

---

# Keybindings

The following keybindings are available in the SQL Workspace:

| Key | Action |
|-----|--------|
| F5 | Execute SQL (selected text or all) |
| F7 | EXPLAIN (tree format) |
| Shift+F7 | EXPLAIN FORMAT=JSON |
| F8 | EXPLAIN ANALYZE |
| Ctrl+Shift+F | Format SQL |
| Ctrl+S | Save SQL file |
| Ctrl+O | Open SQL file |
| Ctrl+L | Clear results |
| Ctrl+E | Export last result set |
| Ctrl+Shift+E | Direct export (stream to file) |
| Ctrl+R | Cycle row display limit |
| Ctrl+Shift+S | Save session log |
| F6 | Switch focus (editor / results) |
| F10 | Exit application |
| Esc | Back to Object Browser |

All keybindings work regardless of which panel has focus.

---

# Design Principles

The SQL Workspace follows these principles:

- Familiar SQL workflow.
- Keyboard-first operation.
- Predictable execution.
- Persistent session history.
- Readable output.
- Excellent support for large SQL statements.
- Transparent SQL execution.
- Simple, focused user experience.