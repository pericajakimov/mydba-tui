# UI Principles

## Purpose

The user interface of `mydba` is designed around one primary objective:

> Allow experienced MySQL DBAs to work faster without requiring them to learn a completely new workflow.

The interface should remain simple, predictable, keyboard-driven, and optimized for terminal environments.

---

# General Principles

The UI should be:

- Keyboard-first
- Clean
- Consistent
- Responsive
- Information-dense without being overwhelming
- Easy to navigate
- Easy to read over SSH

The application should never try to imitate a graphical desktop application. It should embrace the strengths of a terminal interface.

---

# Familiarity

Whenever possible, the interface should behave similarly to tools that MySQL DBAs already know.

Examples include:

- mysql
- mysqlsh
- less
- vim (where appropriate)

The objective is to reduce the learning curve.

---

# Simplicity

Every screen should answer one question:

> "What is the user trying to accomplish right now?"

Only information relevant to the current task should be displayed.

Avoid decorative elements and unnecessary visual complexity.

---

# Keyboard-First Navigation

All application functionality should be accessible using the keyboard.

Mouse interaction, if supported by the underlying framework, is considered optional.

Frequently used actions should require as few key presses as possible.

---

# Discoverability

Users should not need to memorize keyboard shortcuts.

Available actions should always be visible on screen.

Examples include:

- Function key labels
- Action hints
- Navigation hints

The interface should teach itself.

---

# Consistency

The same key should perform the same action throughout the application whenever practical.

Examples:

- Enter opens or selects.
- Esc closes dialogs or returns to the previous screen.
- F5 executes SQL.
- Arrow keys navigate.
- Page Up and Page Down scroll.

Users should never wonder whether a shortcut behaves differently on another screen.

---

# Metadata Before Data

The application is designed primarily for administration.

When browsing database objects, metadata is more valuable than table contents.

Selecting a table should present metadata such as:

- General information
- DDL
- Columns
- Indexes
- Partitions
- Grants
- Dependencies

Reading table data is always an explicit action initiated by the user.

---

# Progressive Disclosure

Information should be revealed gradually.

Start with the information most commonly needed.

Provide additional details only when requested.

This keeps screens uncluttered while still allowing deep inspection.

---

# Readability

Information should be easy to scan quickly.

The interface should use:

- Logical grouping
- Consistent spacing
- Aligned columns
- Meaningful colors
- Syntax highlighting
- Proper indentation

Good readability is more important than maximizing the amount of information on screen.

---

# Color Usage

Colors should communicate meaning rather than decoration.

Examples include:

- Production environment
- Warning states
- Errors
- Active selections
- SQL syntax
- JSON formatting

Color should never be the only indicator of important information.

---

# Environment Awareness

The current environment should always be clearly visible.

Examples:

- Production
- Stage
- QA
- Development

Environment color is defined by the connection profile.

Recommended colors:

- Production → Red
- Stage → Orange
- QA → Blue
- Development → Green

This information should remain visible throughout the session.

---

# Connection Awareness

The header should continuously display the active connection context.

The user should always know:

- Environment
- Connection name
- Server role
- Server type and version
- Current database
- Current user

This minimizes the risk of executing commands on the wrong system.

---

# Fast Navigation

The interface should minimize unnecessary screen transitions.

Common tasks should be reachable in one or two actions.

Returning to previous screens should always be straightforward.

---

# Large Content

The interface must gracefully handle:

- Long SQL statements
- Long stored procedures
- Large DDL definitions
- Wide result sets
- Long JSON documents

Scrolling should always remain smooth and predictable.

---

# Error Handling

Errors should be presented clearly.

The user should receive:

- The MySQL error message
- The failing operation
- No unnecessary technical details

Errors should never leave the application in an inconsistent state.

---

# Performance

The interface should feel responsive.

Metadata should load quickly.

Screen transitions should appear immediate.

Rendering should remain smooth even for large objects.

---

# Focus

Only one area of the interface should receive keyboard input at a time.

The currently focused component should always be visually obvious.

This prevents accidental actions and simplifies navigation.

---

# User Control

The application should never perform potentially expensive operations automatically.

Examples include:

- Reading table data
- Large exports
- Full scans

These actions should always require explicit user confirmation through normal interaction.

---

# Guiding Principle

Every UI decision should support one question:

> "Does this help an experienced MySQL DBA complete everyday work faster while remaining familiar and predictable?"
