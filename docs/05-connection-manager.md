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
- Connect timeout in seconds (default: 10)
- Compressed protocol (default: off)
- Init command (optional, SQL executed on connect)
- Login path (optional, reads credentials from .mylogin.cnf)
- Option file (optional, path to a .my.cnf file)
- Option group suffix (optional, like --defaults-group-suffix)
- SSL configuration (optional)
- SSH tunnel configuration (optional)
- Password (optional, obfuscated if provided)

Passwords should not be stored by default.

Autocommit is always enabled. Transaction control is handled explicitly
by the user via BEGIN/COMMIT or session variable changes.

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
| QA | Light Blue |
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

Available actions on the profile list:

- **Enter** — Connect to the selected profile
- **a** — Add a new profile
- **e** — Edit the selected profile
- **c** — Copy (duplicate) the selected profile
- **d** — Delete the selected profile (with confirmation)

---

# Startup Flow

Application starts.

If command-line connection parameters are provided:

- Connect immediately.

Otherwise:

Display the profile list.

User selects a profile.

The application resolves credentials from all available sources:

1. Profile fields (username, password).
2. Login path from `.mylogin.cnf`.
3. `~/.my.cnf` or the configured option file (`[client]` section).

If all required credentials are available:

- Connect immediately.

If only the username is known (from profile or config file):

- Prompt only for password.

If neither username nor password is available:

- Prompt for both.

The credentials prompt pre-populates any fields already known.

Attempt connection.

On authentication failure:

- Display the MySQL error.
- Show the credentials prompt to correct or provide credentials.

On other connection failure (unreachable host, timeout):

- Display the MySQL error.
- Remain on the profile list.

On success:

- Detect server capabilities.
- Open the application.

---

# Authentication

The Connection Manager supports:

- Username/password authentication
- SSL/TLS connections (with configurable ssl-mode)
- SSH tunnels

Supported SSL modes (matching MySQL `--ssl-mode`):

- DISABLED — No SSL
- PREFERRED — Use SSL if server supports it (default)
- REQUIRED — Require SSL, do not verify certificate
- VERIFY_CA — Require SSL and verify server CA certificate
- VERIFY_IDENTITY — Require SSL, verify CA, and verify server hostname

Authentication failures are reported exactly as returned by MySQL.

No custom interpretation is performed.

---

# SSH Tunnel

Profiles may define an SSH tunnel (jump host) configuration for connecting
to MySQL servers not directly reachable from the local machine.

When a tunnel is configured:

1. An SSH connection is established to the jump host.
2. A local port is forwarded through the tunnel to the remote MySQL server.
3. The MySQL connection is made to `127.0.0.1` on the forwarded port.
4. The tunnel remains active for the entire session.

SSH tunnel fields:

- Host — SSH jump server hostname or IP
- Port — SSH port (default: 22)
- Username — SSH username
- Key File — path to SSH private key (optional)
- Password — SSH password (optional, obfuscated if stored)

Authentication priority:

1. Key file (if provided and exists)
2. Password
3. SSH agent (if available)

---

# Connection Options

## Connect Timeout

Time in seconds to wait for a connection to be established.

Default: 10 seconds.

Useful for detecting unreachable servers quickly in production environments.

## Compressed Protocol

When enabled, uses MySQL protocol compression for data transfer.

Default: off.

Recommended when connecting over high-latency networks or WAN links. Not recommended for local or low-latency connections as compression adds CPU overhead.

## Init Command

An optional SQL statement executed immediately after a successful connection.

Examples:

```
SET SESSION wait_timeout=28800
SET SESSION group_concat_max_len=1048576
SET SESSION sql_mode='TRADITIONAL'
```

This allows customizing the session environment without manual intervention after each connection.

## Autocommit

Autocommit is always enabled and is not configurable per profile.

This matches the default MySQL client behavior. When explicit transaction control is needed, the user should use `BEGIN`/`COMMIT` statements or modify the session variable directly.

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

## Password Obfuscation

When a password is present in a profile, it is obfuscated using XOR with
a machine-derived key and base64 encoding. This prevents casual reading
of passwords in the YAML file.

Stored passwords appear as:

```yaml
password: obf:PaAzNksztZT/1g==
```

If the password field is left empty, the user is prompted on every
connection. If a password is entered, it is saved automatically.

This is not cryptographic security. It is intended to avoid plaintext
passwords being immediately visible when viewing configuration files.

The obfuscation key is derived from the machine identity. Passwords
obfuscated on one machine cannot be decoded on another.

For stronger credential management, use `.mylogin.cnf` (via login_path)
or leave the password empty and enter it on every connection.

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

The Connection Manager supports existing MySQL configuration mechanisms.

## Login Path (.mylogin.cnf)

A profile can reference a login path name. This reads encrypted credentials
stored by `mysql_config_editor`, the same mechanism used by the native
MySQL client tools.

Equivalent to: `mysql --login-path=name`

Example profile:

```yaml
- name: Payments_prod
  environment: prod
  login_path: payments_prod
```

The password (and optionally host/user) is read from `.mylogin.cnf`
without storing it in the mydba profile.

## Option File (.my.cnf)

A profile can reference a specific `.my.cnf` file to read connection
defaults from a named group.

Equivalent to: `mysql --defaults-file=/path --defaults-group-suffix=_name`

Example profile:

```yaml
- name: Reporting
  environment: prod
  option_file: ~/.my.cnf
  option_group: _reporting
```

This reads `[client]` and `[client_reporting]` groups from the specified file.

The connector reads all supported options from the config file, including:

- `user`, `password`
- `host`, `port`
- `compress`
- `connect-timeout`
- `ssl-mode`, `ssl-ca`, `ssl-cert`, `ssl-key`
- `database`

Explicit profile fields always override config file values.

## Priority

When both profile fields and config file values are available:

1. Explicit profile fields (host, port, username, password) always win.
2. Login path credentials from `.mylogin.cnf`.
3. Explicit option file/group values from a custom `.my.cnf`.
4. Automatic fallback to `~/.my.cnf` if it exists (same as native `mysql` client).

If no credentials are available from any source, the user is prompted.

This allows DBAs to reuse existing credentials already configured for
other MySQL tools (`mysql`, `mysqldump`, `mysqlsh`, etc.) without any
additional configuration in mydba.

---

# Command-Line Compatibility

The application supports standard MySQL client connection options.

When connection parameters are provided on the command line, the profile
selection screen is skipped and a direct connection is established.

## Connection Options

| Flag | Long form | Description |
|------|-----------|-------------|
| `-h` | `--host` | Server hostname (default: 127.0.0.1) |
| `-P` | `--port` | Server port (default: 3306) |
| `-u` | `--user` | MySQL username |
| `-p` | `--password` | Password (prompted if given without value) |
| `-D` | `--database` | Default database |
| `-C` | `--compress` | Enable protocol compression |
| | `--connect-timeout` | Connection timeout in seconds |

## Config File Options

| Flag | Long form | Description |
|------|-----------|-------------|
| | `--login-path` | Login path from .mylogin.cnf |
| | `--defaults-file` | Option file path (instead of ~/.my.cnf) |
| | `--defaults-group-suffix` | Option group suffix (e.g. _payments) |

## SSL Options

| Flag | Long form | Description |
|------|-----------|-------------|
| | `--ssl-mode` | DISABLED, PREFERRED, REQUIRED, VERIFY_CA, VERIFY_IDENTITY |
| | `--ssl-ca` | CA certificate path |
| | `--ssl-cert` | Client certificate path |
| | `--ssl-key` | Client key path |

## mydba-Specific Options

| Flag | Long form | Description |
|------|-----------|-------------|
| | `--profile` | Connect using a saved profile by name |
| | `--init-command` | SQL to execute after connecting |
| `-V` | `--version` | Show version and exit |
| | `--help` | Show help and exit |

## Examples

```bash
# Interactive mode (profile selection)
mydba

# Connect to local server
mydba -h 127.0.0.1 -u root -p

# Connect with inline password
mydba -h db.example.com -u admin -pMySecret -D payments

# Use a saved profile
mydba --profile Payments_prod

# Use login path from .mylogin.cnf
mydba --login-path production

# Show version
mydba --version
```

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

After connecting, the application status bar displays:

- Environment (color-coded: PROD=red, STAGE=orange, QA=light blue, DEV=green)
- Connection name
- Server type and version
- Server role (if applicable)
- Instance identifier (Aurora: aurora_server_id, PXC: wsrep_node_name)
- Current database
- Current user

Examples:

```
PROD Payments_writer | Aurora 3.04.3 (InnoDB 8.0.36) | Writer | prod-instance-1 | payments | dba@%
DEV Local | MySQL 8.4.10 | mysql | root@localhost
PROD PXC_node1 | PXC 8.0.35 | node1 | payments | dba@%
```

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

- Display the MySQL error message.

Authentication failures (access denied):

- Show the credentials prompt so the user can correct or provide credentials.

Other failures (unreachable host, timeout, network error):

- Remain on the profile selection screen.

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
