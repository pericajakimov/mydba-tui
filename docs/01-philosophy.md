# Philosophy

## Introduction

The philosophy of `mydba` defines the principles that guide every architectural and implementation decision throughout the project.

Whenever multiple technical solutions are possible, the one that best aligns with this philosophy should be preferred.

The objective is not to build the most feature-rich terminal application, but to build the most effective productivity tool for professional MySQL database administrators.

---

# The DBA Comes First

Every feature should solve a real problem encountered during day-to-day database administration.

Features that exist only because they are technically interesting should be avoided.

The application should optimize the daily workflow of an experienced DBA rather than demonstrate technical capabilities.

---

# Extend the MySQL Ecosystem

`mydba` is designed to complement existing MySQL tools, not replace them.

The workflow should feel familiar to anyone who regularly uses:

- mysql
- mysqlsh
- mysqldump

Whenever possible, conventions already established by these tools should be respected.

Examples include:

- familiar connection parameters
- familiar SQL execution workflow
- familiar vertical output
- familiar terminology
- familiar object names

Learning the application should require minimal effort for existing MySQL users.

---

# Metadata First

The default action when browsing database objects is to inspect metadata, not table contents.

Most administrative work consists of understanding object definitions rather than reading data.

When selecting an object, the application should present information such as:

- general information
- DDL
- columns
- indexes
- partitions
- grants
- dependencies
- statistics

Reading table data should always be an explicit action initiated by the user.

---

# Keyboard First

The application is designed to be operated entirely from the keyboard.

Common operations should require as few keystrokes as possible.

Navigation should be discoverable without memorizing shortcuts.

Whenever practical, available keyboard shortcuts should be visible on screen.

Function keys should be preferred for frequently used actions.

---

# Human Productivity Over Automation

`mydba` is an interactive tool intended for humans.

It is not designed as an automation framework or scripting engine.

Although compatibility with standard MySQL command-line options is desirable, automation is not a primary design goal.

The interface should always prioritize human efficiency over machine integration.

---

# Transparency

The application should never hide what it is doing.

Every SQL statement executed against the server should be visible through the SQL log.

The DBA should always be able to understand:

- what SQL was executed
- when it was executed
- why it was executed

This transparency makes the application easier to trust, learn from, and optimize.

---

# Simplicity

The simplest solution that satisfies the requirements should be preferred.

Avoid unnecessary abstraction.

Avoid unnecessary configuration.

Avoid unnecessary complexity.

New features should integrate naturally into the existing workflow rather than introduce additional concepts.

---

# Modular Design

The project should be organized into independent modules with clear responsibilities.

Examples include:

- Object Browser
- SQL Workspace
- Administration
- Monitoring
- Export Framework
- Connection Manager

Modules should communicate through well-defined interfaces and remain as independent as practical.

---

# SQL Is a First-Class Citizen

SQL is not merely an implementation detail.

Whenever practical, SQL statements should exist as separate resources rather than being embedded inside Python code.

Benefits include:

- easier review
- easier optimization
- easier debugging
- improved readability
- better collaboration between developers and DBAs

Dynamic SQL should only be generated when necessary.

---

# Familiar Before Clever

The application should prefer familiar workflows over novel interfaces.

A DBA should immediately recognize how to perform common tasks without consulting documentation.

Innovation is encouraged only when it clearly improves usability.

---

# Offline by Design

The application should support environments where internet access is unavailable.

Installation should be possible using pre-built offline packages.

External runtime dependencies should be minimized whenever practical.

---

# Production First

The primary deployment target is production tooling servers.

Every design decision should consider:

- reliability
- predictability
- security
- stability

Experimental features should never compromise the core functionality required for production work.

---

# Performance Matters

The application should feel responsive.

Metadata queries should be efficient.

Rendering should remain fast even for large object definitions and result sets.

Resource consumption should remain reasonable for terminal environments.

---

# Readability

Information should be optimized for quick understanding.

Examples include:

- syntax-highlighted SQL
- aligned output
- meaningful colors
- consistent formatting
- logical grouping of related information

The objective is to reduce cognitive load during operational work.

---

# Evolution Through Refinement

The project is expected to evolve over time.

Initial implementations should focus on correctness, simplicity, and usability.

Additional functionality should be introduced through iterative refinement rather than premature complexity.

Every new feature should strengthen the existing philosophy instead of changing it.
