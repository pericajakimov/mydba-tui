# Configuration

## Purpose

The Configuration subsystem manages all application settings that control the behavior of `mydba`.

Configuration is intentionally separated from application logic to make the tool predictable, portable, and easy to maintain.

The primary goal is to provide sensible defaults while allowing users and teams to customize the application where appropriate.

---

# Design Goals

The Configuration subsystem should:

- Be simple.
- Be human-readable.
- Support versioning.
- Separate application settings from connection profiles.
- Be portable across Linux, macOS, and Windows.
- Remain backwards compatible whenever possible.

---

# Configuration Philosophy

Configuration should describe **how the application behaves**, not **what it does**.

Examples include:

- Theme selection
- Refresh intervals
- Default export directory
- SQL logging
- Editor preferences

Configuration should never contain application state.

---

# Configuration Categories

Configuration is divided into four independent areas:

- Application Settings
- Connection Profiles
- User-Defined Rules
- Theme Settings

Each category has its own configuration file.

---

# Application Settings

Application settings control global application behavior.

Examples include:

- Default theme
- Monitoring refresh interval
- SQL logging options
- Application logging level
- Default export directory
- Default page size
- Default editor behavior

These settings apply to all connections.

---

# Connection Profiles

Connection profiles define how to connect to MySQL servers.

Each profile represents exactly one database endpoint.

Typical fields include:

- Connection name
- Environment
- Host
- Port
- Username (optional)
- Default database (optional)
- SSL configuration (optional)
- SSH tunnel configuration (optional)

Passwords should not be stored by default.

Connection profiles are described in detail in the **Connection Manager** document.

---

# User-Defined Rules

Certain application behavior is environment-specific.

Examples include:

- User group definitions
- Role classification rules
- Future custom object classifications

These rules are intentionally separated from application code so they can be adapted without modifying the program.

The initial implementation focuses on user grouping rules used by the development team.

---

# Theme Settings

Theme configuration controls only the visual appearance.

Examples include:

- Colors
- Highlight styles
- Status colors
- Selection colors
- Environment colors

Themes never modify application behavior.

---

# Configuration Storage

Configuration files are stored as YAML.

YAML was chosen because it:

- Is human-readable
- Supports comments
- Is easy to edit manually
- Works well with version control
- Is widely understood by DBAs and engineers

The configuration directory contains:

- `settings.yaml` — Application settings
- `profiles.yaml` — Connection profiles

---

# Default Configuration

The application should start successfully using only default settings.

A first-time user should not be required to configure the application before connecting to a database.

---

# First-Time Experience

If no configuration exists:

- Create default application settings automatically.
- Present an empty profile list.
- Allow the user to create a new profile.
- Allow direct connection using command-line options or existing MySQL configuration files.

The absence of configuration should never prevent the application from starting.

---

# Settings Screen

`mydba` provides a dedicated Settings screen.

This screen allows modification of application configuration without manually editing configuration files.

Typical settings include:

- Theme
- Logging
- Monitoring refresh interval
- Export defaults
- Editor preferences

Additional settings may be added in future versions.

---

# Environment Awareness

Environment information belongs to connection profiles.

Supported environments include:

- Production
- Stage
- QA
- Development

The environment determines the color displayed in the application header.

---

# Logging Configuration

Configuration should allow independent control of:

- SQL logging
- Application logging

Possible options include:

- Enable or disable SQL logging
- SQL log location
- Application log location
- Log verbosity

SQL logging is enabled by default during early development to ensure complete transparency of generated SQL.

---

# Export Configuration

Global export settings may include:

- Default export directory
- Preferred export format
- CSV delimiter options
- Text encoding

Individual exports may override these defaults when necessary.

---

# Monitoring Configuration

Monitoring settings may include:

- Refresh interval
- Graph history length
- Enabled widgets

The Monitoring module should continue functioning with sensible defaults if these settings are absent.

---

# Editor Configuration

The SQL editor may expose configurable behavior such as:

- Tab width
- Indentation
- Line wrapping
- Preferred SQL formatting options

Autocomplete and advanced editor features may introduce additional settings in future versions.

---

# Compatibility

Configuration changes should preserve backwards compatibility whenever practical.

If configuration formats evolve, the application should migrate older configurations automatically whenever possible.

---

# Configuration Directory

All configuration files are stored in:

```
~/.config/mydba/
```

This path is used consistently on all supported platforms:

- Linux: `~/.config/mydba/`
- macOS: `~/.config/mydba/`
- Windows: `C:\Users\<username>\.config\mydba\`

The decision to use a single path across platforms simplifies documentation, tooling, and portability for DBAs who work across multiple systems.

---

# Portability

Configuration should work consistently on:

- Linux
- macOS
- Windows

Platform-specific behavior should be minimized.

---

# Future Enhancements

Possible future additions include:

- Multiple named configuration sets
- Environment-specific settings
- Team-wide shared configuration
- Import and export of settings
- Configuration validation
- Plugin-specific configuration

These additions should integrate without changing the existing configuration model.

---

# Design Principles

The Configuration subsystem follows these principles:

- Simple defaults.
- Human-readable configuration.
- Clear separation of responsibilities.
- Portable across supported platforms.
- Easy to customize.
- Backwards compatible.
- Predictable behavior.
