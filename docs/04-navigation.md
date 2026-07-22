# Navigation

## Purpose

The navigation model of `mydba` is designed around one principle:

> Navigation should be obvious without requiring the user to memorize keyboard shortcuts.

The application should always make it clear:

- Where the user currently is.
- Which actions are available.
- How to return.
- How to perform the next common task.

---

# Navigation Philosophy

The application is keyboard-first.

Mouse interaction is optional and should never be required.

Navigation should remain consistent across all screens.

The user should never need to remember hidden shortcuts.

Available actions should always be visible.

---

# Main Navigation Model

The application follows a hierarchical navigation model.

```
Connection
    ↓

Home

    ├── Object Browser
    │
    ├── SQL Workspace
    │
    ├── Administration
    │
    ├── Monitoring
    │
    └── Settings
```

Each module owns its internal navigation.

Leaving a module always returns to the previous level.

---

# Screen Layout

Every screen follows the same layout.

```
+------------------------------------------------------------------+
| Header                                                           |
+------------------------------------------------------------------+

|                                                                  |
|                                                                  |
|                        Screen Content                            |
|                                                                  |
|                                                                  |

+------------------------------------------------------------------+
| F1 Help  F2 ...  F3 ...  Enter Open  Esc Back  F10 Exit          |
+------------------------------------------------------------------+
```

The footer always displays the actions available for the current screen.

---

# Header

The header provides constant awareness of the current connection.

It displays:

- Environment
- Connection name
- Server role
- Server type and version
- Current database
- Current user

This information remains visible throughout the session.

---

# Footer

The footer acts as the primary navigation guide.

Only actions valid for the current screen are displayed.

Users should not need to remember keyboard shortcuts.

---

# Primary Keys

## Enter

Primary action.

Examples:

- Open object
- Select item
- Confirm dialog
- Show details

---

## Esc

Return to the previous screen.

If already at the top level, closes dialogs or cancels the current operation.

Esc never performs destructive actions.

---

## Arrow Keys

Move selection.

Supported everywhere appropriate.

---

## Page Up / Page Down

Scroll large content.

Examples:

- SQL
- DDL
- JSON
- Result sets
- Help pages

---

## Home / End

Jump to beginning or end of the current view where applicable.

---

# Function Keys

Function keys provide quick access to common actions.

The exact actions depend on the current screen.

Examples include:

- Execute SQL
- Explain query
- Export data
- Refresh information
- Help

Every function key shown in the footer must be valid for the current screen.

---

# Object Browser Navigation

Navigation follows a tree structure.

```
Schemas

    sales
        Tables
        Views
        Procedures
        Functions
        Events
        Triggers

    reporting
        ...

    mysql
        ...

    sys
        ...
```

Selecting an object opens its metadata view.

No table data is loaded automatically.

---

# SQL Workspace Navigation

The SQL Workspace behaves similarly to a traditional SQL editor.

The editor occupies the upper portion of the workspace.

Executed results appear below the editor in chronological order.

Multiple executions remain visible until the workspace is cleared or the application exits.

---

# Result Navigation

Result sets support keyboard navigation.

Users can:

- Move between rows.
- Scroll horizontally.
- Scroll vertically.
- Switch to vertical output when appropriate.

Large datasets should remain navigable without leaving the workspace.

---

# Dialog Navigation

Dialogs are modal.

While a dialog is open:

- Only the dialog receives keyboard input.
- Esc closes the dialog without performing the action.
- Enter activates the focused button.

For destructive actions (delete, disconnect), the safe option (No/Cancel)
is focused by default. The user must Tab to the destructive option and
press Enter to confirm.

---

# Search

If a screen supports searching, it operates only within the current context.

Examples:

- Searching tables inside the selected schema.
- Searching variables.
- Searching process list entries.

Typing should never unexpectedly activate search while another component (such as the SQL editor) has focus.

---

# Focus Management

Only one component may have keyboard focus.

Examples include:

- Object tree
- Metadata panel
- SQL editor
- Result viewer
- Dialog

The focused component should always be visually distinguishable.

---

# Multiple Sessions

Each running instance of `mydba` owns a single database connection.

Working with multiple servers simultaneously is achieved by starting multiple application instances.

Examples:

- Multiple `screen` sessions on Linux.
- Multiple terminal windows.
- Multiple iTerm2 tabs.

The application itself does not manage multiple simultaneous connections.

---

# Disconnect

Disconnecting ends the current application session.

A new connection starts a new application instance.

This guarantees:

- Clean application state.
- Empty SQL workspace.
- Fresh connection.
- New MySQL connection ID.

This behavior intentionally matches the workflow of the traditional MySQL client.

---

# Navigation Goals

The navigation model is designed to achieve the following objectives:

- Minimize keystrokes.
- Eliminate hidden workflows.
- Keep important actions visible.
- Preserve familiar MySQL workflows.
- Support efficient operation over SSH.
- Make the application easy to learn and easy to remember.
