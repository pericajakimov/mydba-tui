# ADR-0006: One Endpoint per Connection Profile

- **Status:** Accepted
- **Date:** 2026-07-17

---

# Context

A connection profile defines how `mydba` connects to a database server.

Several approaches were considered:

1. A profile containing multiple endpoints (for example, Writer and Reader).
2. A profile representing an entire cluster.
3. A profile representing exactly one endpoint.

Because the primary users are DBAs, the connection model should always make it obvious which endpoint they are connected to.

---

# Decision

A connection profile represents **exactly one database endpoint**.

Examples:

```
Payments_perica      -> Writer endpoint

Payments_user1       -> Writer endpoint

Payments_RO          -> Reader endpoint
```

If both Writer and Reader endpoints are needed, two independent profiles are created.

---

# Rationale

DBAs think in terms of endpoints rather than clusters.

Typical tasks are performed specifically against either:

- Writer endpoint
- Reader endpoint
- Replica
- Standalone server

Keeping one endpoint per profile removes ambiguity and makes the active target immediately clear.

---

# Profile Identity

A profile is uniquely identified by:

```
Connection Name
+
Stored Username (optional)
```

Examples:

```
Payments [perica]

Payments [appuser]

Payments_RO
```

This allows multiple users to maintain separate profiles for the same endpoint without modifying profile names.

If no username is stored, the user is prompted during connection.

---

# Environment Grouping

Profiles are grouped by environment.

Typical groups include:

- PROD
- STAGE
- QA
- DEV

On shared tooling servers, a single environment group is common.

On a developer laptop, profiles from multiple environments may coexist.

Grouping improves navigation while keeping the profile list simple.

---

# Profile Display

The connection selection dialog displays only:

- Environment group
- Connection name

No additional metadata such as:

- Last connected time
- Server version
- Host name
- Connection history

is shown in the profile list.

The goal is to keep profile selection fast and uncluttered.

---

# Active Profile

After connecting, the active profile name is displayed permanently in the application header.

Within the profile selection dialog, the currently active profile may be visually marked to indicate the existing connection.

Outside of that dialog, the header provides the necessary context.

---

# Backend Detection

The profile does **not** specify the database platform.

After connecting, `mydba` automatically detects characteristics of the target server, such as:

- Oracle MySQL
- AWS Aurora
- Percona Server
- Percona XtraDB Cluster

Available features are then adjusted automatically.

This keeps profiles simple and avoids configuration drift.

---

# Authentication

A profile may optionally store:

- Username
- SSL settings
- SSH tunnel configuration

Passwords should generally **not** be stored.

Instead:

- Prompt for password.
- Use `.my.cnf` when appropriate.
- Use `.mylogin.cnf` when available.

This aligns with existing MySQL practices and improves security.

---

# Connection Failure

If a connection attempt fails:

- Display the MySQL error message.
- Return to the profile selection dialog.

No special handling is required for:

- Invalid credentials
- Expired passwords
- SSL errors
- SSH tunnel failures

The underlying MySQL error should be presented to the user.

---

# Reconnection

If the active connection is lost:

- Reconnect uses the **same profile**.
- The SQL editor remains intact.
- A new MySQL connection is established.
- A new server connection ID is assigned.

This allows users to recover from transient failures without losing their work.

---

# Alternatives Considered

## Multiple Endpoints per Profile

Rejected.

Combining Writer and Reader endpoints in a single profile introduces unnecessary complexity:

- Endpoint selection dialogs
- Hidden state
- Additional UI
- Higher risk of executing against the wrong server

Independent profiles provide a clearer and safer workflow.

---

## Cluster-Based Profiles

Rejected.

A cluster is an operational concept.

Connections are always established to a specific endpoint.

Representing the endpoint directly keeps the configuration aligned with actual usage.

---

# Consequences

Each connection profile represents a single, explicit connection target.

This simplifies:

- Configuration
- Connection logic
- Header display
- Reconnection
- User understanding

The approach also aligns naturally with the application's **one process, one connection** architecture.

---

# Future Considerations

Future versions may introduce profile import/export or synchronization features.

Regardless of future enhancements, the core principle remains:

> One connection profile represents one endpoint and one connection target.
