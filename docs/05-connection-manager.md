# Connection Manager

## Purpose

The Connection Manager is responsible for establishing and managing database connections.

It provides a secure and predictable way to connect to MySQL-compatible databases while minimizing repetitive typing and preserving the workflow familiar to MySQL DBAs.

The Connection Manager is the first screen presented when the application starts unless sufficient connection information is provided through the command line.

---

# Design Goals

The Connection Manager should:

- Minimize connection setup time.
- Keep credentials secure.
- Support shared tooling servers.
- Support local developer environments.
- Remain compatible with existing MySQL tooling.
- Never hide connection details from the user.

---

# Connection Philosophy

A connection profile represents exactly one database endpoint.

Examples:

- Aurora Writer endpoint
- Aurora Reader endpoint
- Standalone MySQL server
- Percona Server
- PXC node

One profile never contains multiple endpoints.

---

# Profile Structure

A profile may contain:

- Connection name
- Environment
- Hostname
- Port
- Username (optional)
- Default database (optional)
- SSL configuration (optional)
- SSH tunnel configuration (optional)
- Stored password (optional)

Passwords should not be stored by default.

---

# Connection Name

The connection name is the primary identifier shown to the user.

It should be meaningful to the DBA.

Examples:

```
Payments_perica
Payments_user1
Payments_RO
Inventory
Reporting
```

The connection name should be unique.

If usernames are included in the naming convention, uniqueness is naturally preserved.

---

# Environment

Each profile belongs to an environment.

Supported values:

- Production
- Stage
- QA
- Development

The environment is used for:

- Visual identification
- Header display
- Color selection

Recommended colors:

| Environment | Color |
|-------------|-------|
| Production | Red |
| Stage | Orange |
| QA | Blue |
| Development | Green |

---

# Profile List

The profile list displays only:

- Environment group
- Connection name

No additional metadata is displayed.

Examples of information intentionally omitted:

- Last connection time
- Number of connections
- Server version

The list should remain simple and easy to scan.

---

# Startup Flow

Application starts.

If command-line connection parameters are provided:

- Connect immediately.

Otherwise:

Display the profile list.

User selects a profile.

If the profile already contains a username:

- Prompt only for password.

Otherwise:

- Prompt for username.
- Prompt for password.

Attempt connection.

On success:

- Detect server capabilities.
- Open the application.

---

# Authentication

The Connection Manager supports:

- Username/password authentication
- SSL authentication
- SSH tunnels

Authentication failures are reported exactly as returned by MySQL.

No custom interpretation is performed.

---

# Password Handling

Passwords should not be stored unless explicitly configured.

Preferred workflow:

Store:

- Endpoint
- Username

Request:

- Password

Every connection.

This reduces the risk of credential leakage on shared systems.

---

# Shared Tooling Servers

Production tooling servers are shared by multiple administrators.

Typical characteristics:

- Shared Linux account.
- Shared profile directory.
- Individual MySQL credentials.

Connection profiles therefore represent database endpoints rather than individual users.

---

# Local Workstations

Local workstations are typically used by a single DBA.

Additional convenience features are acceptable.

Examples:

- Stored passwords
- Local encrypted password storage

These are optional and should never affect shared environments.

---

# Existing MySQL Configuration

The Connection Manager should support existing MySQL configuration mechanisms.

Examples include:

- `.my.cnf`
- `.mylogin.cnf`

This allows DBAs to reuse existing credentials already configured for other MySQL tools.

---

# Command-Line Compatibility

The application should support standard MySQL connection options whenever practical.

Examples include:

```
-h
-P
-u
-p
-D
```

This compatibility exists primarily for familiarity and convenience.

Interactive profile selection remains the primary workflow.

---

# Connection Detection

Immediately after a successful connection, the application detects server characteristics.

Examples include:

- Oracle MySQL
- AWS Aurora
- Percona Server
- Percona XtraDB Cluster
- MariaDB

Detected capabilities determine which features are available throughout the application.

---

# Header Information

After connecting, the application header displays:

- Environment
- Connection name
- Server role
- Server type and version
- Current database
- Current user

This information remains visible for the entire session.

---

# Server Role

If supported by the connected platform, the application identifies the server role.

Examples:

Aurora:

- Writer
- Reader

Traditional replication:

- Primary
- Replica

If the role cannot be determined, no role is displayed.

---

# Reconnect

Reconnect is an explicit user action.

It establishes a new database connection using the current profile.

The SQL Workspace remains unchanged.

A successful reconnect results in a new MySQL connection ID.

---

# Failed Connection

If a connection attempt fails:

- Display the MySQL error.
- Return to the profile selection screen.

The application does not attempt automatic retries.

---

# Session Lifetime

One application instance owns exactly one database connection.

Changing to another server requires:

- Exiting the current session.
- Starting a new application instance.

This guarantees a clean application state and matches the workflow of the traditional MySQL client.

---

# Design Principles

The Connection Manager is designed around the following principles:

- Simple profile management.
- Secure default behavior.
- Compatibility with existing MySQL tooling.
- Clear environment awareness.
- One profile per endpoint.
- One application instance per connection.
- Explicit user control.
