# Security

## Purpose

`mydba` is an interactive database administration tool intended for experienced MySQL DBAs.

The goal of the security model is to minimize credential exposure while remaining compatible with existing MySQL tooling and operational workflows.

Security should never come at the expense of usability, but convenience must never compromise production environments.

---

# Design Principles

The security model follows these principles:

- Secure by default.
- Least privilege.
- Explicit user actions.
- Transparency.
- Compatibility with existing MySQL tools.
- No hidden credentials.
- No hidden SQL.

---

# Threat Model

The primary deployment scenarios are:

- Shared Linux tooling servers
- Individual DBA workstations

These environments have different security requirements and are treated differently.

---

# Shared Tooling Servers

A shared tooling server is the primary production deployment model.

Typical characteristics:

- Shared EC2 instance
- Shared Linux account (commonly `root`)
- Multiple DBAs
- Multiple DevOps engineers
- Multiple BI users

Connection profiles are shared.

Database credentials are **not**.

---

# Local Workstations

A local workstation is typically used by a single DBA.

Convenience features are acceptable provided they remain optional.

Examples include:

- Stored passwords
- Encrypted local password storage

These features should never be enabled automatically.

---

# Connection Profiles

A connection profile represents a single database endpoint.

Profiles may contain:

- Connection name
- Environment
- Hostname
- Port
- Username (optional)
- Default database (optional)
- SSL settings (optional)
- SSH tunnel settings (optional)

Passwords are optional and should not be stored by default.

---

# Password Policy

The preferred workflow is:

Store:

- Connection information
- Username

Prompt for:

- Password

Every connection.

This minimizes the impact of compromised profile files.

---

# Stored Passwords

Password storage is supported only as a convenience feature.

Typical use cases include:

- Local laptop
- Dedicated monitoring accounts
- Read-only operational accounts

Stored passwords are obfuscated (XOR + base64 with a machine-derived key)
to prevent plaintext exposure in configuration files. This is not
cryptographic security but prevents casual reading.

Stored passwords should never be required for normal operation.

---

# Existing MySQL Credentials

`mydba` should integrate with existing MySQL credential mechanisms whenever possible.

Supported sources include:

- `.mylogin.cnf` (via `login_path` in profile)
- `.my.cnf` (via `option_file` and `option_group` in profile)

This allows users to reuse credentials already managed by standard MySQL tools.

Priority when connecting:

1. Explicit profile fields always win.
2. Login path credentials from `.mylogin.cnf`.
3. Option file/group values from `.my.cnf`.

---

# SSL Support

SSL behavior is controlled by the `ssl_mode` setting in each profile.

Supported modes:

- DISABLED — No SSL connection
- PREFERRED — Use SSL if the server supports it (default)
- REQUIRED — Require SSL, do not verify certificate
- VERIFY_CA — Require SSL and verify server CA certificate
- VERIFY_IDENTITY — Require SSL, verify CA, and verify server hostname

When a CA certificate, client certificate, or client key is provided, they are passed to the MySQL driver.

SSL validation errors are reported exactly as returned by the driver.

---

# SSH Tunnels

Profiles may optionally define SSH tunnel parameters.

If configured:

- Establish the SSH tunnel to the jump host first.
- Forward a local port to the remote MySQL server.
- Connect MySQL through the forwarded port.
- Report connection failures without modification.

Supported SSH authentication:

- Key-based authentication (RSA keys, SSH agent)
- Password authentication (obfuscated in profiles.yaml)

Tunnel configuration is stored only as connection metadata.
The tunnel remains active for the duration of the connection
and is closed automatically on disconnect.

---

# Authentication

Supported authentication mechanisms depend on the capabilities of the underlying MySQL driver.

The application should not impose additional authentication restrictions beyond those supported by MySQL.

---

# Authorization

`mydba` never attempts to elevate privileges.

The application operates entirely within the permissions granted to the authenticated MySQL account.

Unavailable functionality should fail naturally with the corresponding MySQL error.

---

# SQL Transparency

Every SQL statement executed by the application is written to the SQL log.

This includes:

- User SQL
- Metadata queries
- Monitoring queries
- Administrative queries

The SQL log intentionally contains **only SQL**.

No application logging or debugging information is mixed into this file.

---

# Application Logging

Application logging is separate from SQL logging.

Typical entries include:

- Startup
- Shutdown
- Internal errors
- Python exceptions
- Debug messages

Application logs must never contain passwords.

---

# Sensitive Information

The application must never write the following to any log:

- Passwords
- Authentication tokens
- Private keys
- SSL private key contents

Only non-sensitive connection metadata may appear in logs.

---

# SQL Injection

All internally generated SQL should use parameterized queries whenever practical.

Dynamic SQL should be generated only when required and only from validated metadata.

The application never executes arbitrary SQL constructed from untrusted input.

---

# Configuration Files

Configuration files should remain human-readable whenever practical.

Sensitive values should be isolated from ordinary configuration wherever possible.

---

# Production Awareness

Production environments are visually distinguished using the environment color defined by the connection profile.

Recommended mapping:

| Environment | Color |
|-------------|-------|
| Production | Red |
| Stage | Orange |
| QA | Blue |
| Development | Green |

The environment indicator remains visible throughout the session to reduce the risk of accidental execution on the wrong system.

---

# Multiple Sessions

Each application instance owns a single database connection.

Working on multiple servers simultaneously is achieved by launching multiple `mydba` instances.

This reduces the risk of confusing active connections and keeps session context isolated.

---

# Error Reporting

Authentication and connection errors should be presented exactly as returned by MySQL whenever practical.

The application should avoid hiding or reinterpreting server error messages.

---

# Future Enhancements

Possible future improvements include:

- OS keychain integration
- Hardware-backed secret storage
- MFA-aware authentication workflows
- Credential providers
- Cloud-native authentication plugins

These enhancements should integrate without changing the existing connection model.

---

# Design Principles

The Security model follows these principles:

- Secure defaults.
- Minimal credential exposure.
- Compatibility with existing MySQL tooling.
- Transparent operation.
- Separate SQL and application logging.
- Least privilege.
- Predictable behavior.
- No hidden security mechanisms.
