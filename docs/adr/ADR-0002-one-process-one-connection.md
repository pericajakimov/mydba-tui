# ADR-0002: One Process, One Database Connection

- **Status:** Accepted
- **Date:** 2026-07-17

---

# Context

One of the early architectural decisions was determining how `mydba` should manage database connections.

Several approaches were considered:

1. A single application managing multiple simultaneous connections.
2. Multiple tabs, each connected to a different server.
3. One application process connected to exactly one database server.

Because `mydba` is intended primarily for professional DBAs working over SSH, the connection model should match the workflows already used with the MySQL command-line client.

---

# Decision

A single `mydba` process manages exactly **one active database connection**.

Working with multiple database servers simultaneously is achieved by starting multiple independent `mydba` instances.

Examples include:

- Multiple `screen` sessions on Linux tooling servers.
- Multiple `tmux` panes.
- Multiple iTerm2 tabs on macOS.
- Multiple terminal windows.

---

# Rationale

This approach closely matches the behavior of the standard MySQL client.

Advantages include:

- No ambiguity about the active server.
- No accidental execution against the wrong database.
- Simpler application architecture.
- Simpler connection lifecycle.
- Simpler transaction handling.
- Lower memory usage.
- Easier debugging.

Each application instance has a single execution context.

---

# Alternatives Considered

## Multiple Connections Inside One Process

Rejected.

Although technically possible, it introduces additional complexity:

- Connection switching
- Session state management
- Active transaction tracking
- Query routing
- Multiple SQL histories
- Multiple monitoring contexts
- Higher risk of user error

The additional complexity provides little practical benefit for the intended users.

---

## Tab-Based Connections

Rejected.

Graphical database tools commonly use tabs for multiple connections.

`mydba` intentionally follows the workflow of terminal-based MySQL administration rather than desktop IDEs.

Users already understand how to work with multiple terminal sessions.

---

## Automatic Reconnection to Different Servers

Rejected.

Changing the target server should start a completely new session.

The user should intentionally disconnect and reconnect rather than silently changing the execution context.

---

# Consequences

Each application instance owns:

- One MySQL connection
- One SQL Workspace
- One Object Browser
- One Monitoring page
- One Administration context
- One SQL log
- One application log

Session state never spans multiple servers.

---

# Reconnecting

If the current connection is lost:

- The user may reconnect to the **same profile**.
- The SQL editor contents remain intact.
- A new MySQL connection is established.
- A new server connection ID is assigned.
- Session-specific server state is reset.

This provides convenience without changing the application's execution model.

---

# Changing Servers

Connecting to a different server is intentionally treated as starting a new session.

Typical workflow:

```
Exit mydba

        ↓

Start mydba

        ↓

Select another profile

        ↓

Connect
```

This guarantees that no state from the previous server is carried over unintentionally.

---

# Benefits

The chosen architecture provides:

- Clear execution context.
- Reduced cognitive load.
- Familiar command-line workflow.
- Simpler implementation.
- Lower maintenance cost.
- Better reliability.

---

# Future Considerations

This decision does not prevent external tools from launching multiple `mydba` instances.

Future integrations may automate opening multiple sessions, but each session will continue to follow the **one process, one connection** model.
