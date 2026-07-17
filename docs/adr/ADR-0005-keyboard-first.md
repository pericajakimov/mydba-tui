# ADR-0005: Keyboard-First User Interface

- **Status:** Accepted
- **Date:** 2026-07-17

---

# Context

The primary users of `mydba` are professional MySQL DBAs.

They spend most of their working day:

- Connected over SSH
- Working in terminal sessions
- Using keyboard-driven tools such as:
  - `mysql`
  - `mysqlsh`
  - `less`
  - `vim`
  - `screen`
  - `tmux`

Unlike graphical database IDEs, mouse interaction is often unavailable or inconvenient.

The user interface should therefore optimize for keyboard efficiency while remaining easy to learn.

---

# Decision

`mydba` adopts a **keyboard-first** interaction model.

Every commonly used operation must be accessible directly from the keyboard.

Mouse support may exist where provided by the terminal, but it is never required.

---

# Rationale

A keyboard-first interface offers several advantages:

- Faster navigation.
- Efficient remote operation.
- Consistent SSH experience.
- Familiar workflow for DBAs.
- Accessibility without relying on terminal mouse support.

The goal is to make `mydba` feel like a natural extension of the existing MySQL command-line ecosystem.

---

# Function Keys

The primary navigation mechanism uses function keys.

Examples include:

| Key | Purpose |
|------|---------|
| Enter | Open selected item |
| Esc | Back / Close dialog |
| F5 | Execute SQL |
| F6 | EXPLAIN (Tree) |
| F7 | EXPLAIN (JSON) |
| F8 | EXPLAIN ANALYZE |

Additional function keys may be introduced as the application grows.

---

# Visible Navigation

Users should never need to memorize keyboard shortcuts.

Every screen should display the actions that are currently available.

Typical footer:

```
Enter Open

F5 Execute

F6 Explain

Esc Back
```

The available actions change depending on the active screen.

---

# Discoverability

Navigation should be self-explanatory.

A user launching `mydba` for the first time should be able to discover common actions simply by looking at the interface.

Documentation should reinforce the interface rather than compensate for hidden shortcuts.

---

# Consistency

The same key should always perform the same logical action.

Examples:

- `Esc` always returns to the previous context or closes the current dialog.
- `Enter` always activates or opens the selected item.
- `F5` always executes SQL when the SQL Workspace has focus.

Keys should not change meaning arbitrarily between screens.

---

# Context Awareness

Keyboard actions are interpreted according to the active component.

Examples:

- In the SQL editor, typing `/` inserts a slash character.
- In a future search field, `/` may begin a search.
- Outside editable controls, function keys perform navigation actions.

Input intended as SQL should never be intercepted by unrelated shortcuts.

---

# Multiple Instances

Working with multiple servers simultaneously is achieved by opening multiple `mydba` instances.

Examples:

- Multiple `screen` sessions.
- Multiple `tmux` panes.
- Multiple terminal tabs.
- Multiple terminal windows.

Keyboard behavior remains identical in every instance.

---

# Alternatives Considered

## Mouse-First Interface

Rejected.

This does not align with the workflow of terminal-based DBAs and is unreliable in many SSH environments.

---

## Complex Keyboard Shortcuts

Examples:

- `Ctrl+Shift+Alt+...`
- Extensive use of `Alt+Number`
- IDE-style shortcut combinations

Rejected.

Such shortcuts are difficult to remember and vary across terminal emulators and operating systems.

Function keys provide a simpler and more consistent user experience.

---

## Command Palette

A command palette may be introduced in the future as an optional convenience feature.

It is not part of the initial navigation model.

The primary workflow remains direct keyboard navigation using visible actions.

---

# Consequences

All interactive features should be designed with keyboard usability in mind.

New screens should define:

- Primary action
- Back action
- Navigation keys
- Function key assignments

Every screen should expose these actions visually.

---

# Future Considerations

Future enhancements may include:

- User-configurable key bindings
- Additional keyboard shortcuts
- Command palette
- Vim-style navigation modes
- Accessibility improvements

Any future additions must preserve the project's guiding principle:

> A professional MySQL DBA should be able to use the entire application efficiently without touching a mouse.
