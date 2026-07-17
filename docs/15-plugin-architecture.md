# Plugin Architecture

## Purpose

The Plugin Architecture defines how `mydba` can be extended without modifying its core codebase.

The initial version of `mydba` will ship with all required functionality built in. Plugin support is designed from the beginning so that future features can be added cleanly without requiring architectural changes.

Plugins are intended to extend the application, **not** to replace or modify core behavior.

---

# Design Goals

The plugin system should:

- Be simple.
- Be optional.
- Be stable.
- Have well-defined interfaces.
- Prevent plugins from affecting unrelated modules.
- Allow third-party extensions in the future.

---

# Philosophy

The core application should remain:

- Small
- Predictable
- Stable
- Fully usable without plugins

Plugins should only add capabilities.

The application must never depend on an external plugin for normal operation.

---

# Core vs Plugins

The following functionality is considered part of the core application:

- Connection Manager
- Object Browser
- SQL Workspace
- Administration
- Monitoring
- Rendering
- Export Framework
- Settings
- Logging

These components are not plugins.

---

# Initial Plugin Targets

The architecture should initially support extension of:

- Exporters
- Object inspectors
- Monitoring widgets
- Server-specific features
- Utility tools

Additional extension points may be introduced later.

---

# Export Plugins

Exporters are the primary example of a plugin.

Each exporter implements the common exporter interface.

Examples:

- CSV
- TSV
- SQL INSERT
- JSONL

Future plugins might provide:

- Excel
- Parquet
- XML
- HTML
- Markdown

The SQL execution engine interacts only with the exporter interface.

---

# Monitoring Plugins

Monitoring plugins may provide additional metrics or visualizations.

Examples:

- Aurora-specific metrics
- Galera/PXC status
- Group Replication status
- Custom operational graphs

Plugins should only be loaded when the connected server supports the required functionality.

---

# Server-Specific Plugins

Some database platforms expose vendor-specific functionality.

Examples include:

- AWS Aurora
- Percona Server
- Percona XtraDB Cluster

The application detects server capabilities after connecting.

Plugins are enabled only when appropriate.

The base application remains vendor-neutral.

---

# Object Inspector Plugins

Future plugins may provide additional metadata views.

Examples:

- Partition visualization
- Index analysis
- Statistics analysis
- Custom dependency analysis

These plugins add new inspection pages without changing the existing Browser navigation.

---

# Utility Plugins

Future utility plugins might include:

- Online schema change helpers
- Backup integrations
- Diagnostic tools
- Data comparison tools
- Custom DBA workflows

These remain independent from the core application.

---

# Plugin Discovery

Plugins should be discovered automatically during application startup.

Only successfully loaded plugins are registered.

A faulty plugin must not prevent the application from starting.

Plugin loading failures should be reported in the application log.

---

# Plugin Registration

Each plugin registers itself through a well-defined interface.

Typical registration includes:

- Plugin name
- Plugin version
- Supported extension point
- Supported server types

Registration should require minimal boilerplate.

---

# Plugin Isolation

Plugins should communicate with the application only through published interfaces.

Plugins should not access internal application state directly.

This reduces coupling and improves long-term maintainability.

---

# Server Awareness

Plugins may declare server compatibility.

Examples:

- Oracle MySQL
- AWS Aurora
- Percona Server
- Percona XtraDB Cluster

The application should activate only compatible plugins for the connected server.

---

# Configuration

Plugins may define their own configuration.

Plugin configuration should be stored separately from the core application configuration.

A plugin should continue working with sensible defaults if no explicit configuration exists.

---

# User Interface

Plugins should integrate naturally with the existing user interface.

Examples include:

- Additional Browser pages
- Additional Monitoring widgets
- Additional Export formats
- Additional Settings pages

Plugins should follow the same UI principles as the core application.

---

# Security

Plugins execute with the same privileges as the application.

Plugins should never receive database credentials directly.

They should use the existing database connection provided by the application.

---

# Logging

Plugins should use the standard application logging framework.

Any SQL executed by a plugin must also appear in the SQL log.

This preserves the project's principle of SQL transparency.

---

# Version Compatibility

The plugin interface should remain stable whenever possible.

Breaking changes should be introduced only in major application versions.

Plugins should be able to declare the minimum supported application version.

---

# Initial Scope

The initial release of `mydba` does not require third-party plugins.

The plugin architecture exists to ensure that future expansion can occur without redesigning the core application.

---

# Design Principles

The Plugin Architecture follows these principles:

- Core functionality first.
- Optional extensions.
- Stable public interfaces.
- Strong isolation.
- Server-aware activation.
- Consistent user experience.
- SQL transparency.
- Long-term extensibility.
