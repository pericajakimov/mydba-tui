# Vision

## Purpose

`mydba` exists to make everyday MySQL administration faster, simpler, and more efficient from the terminal.

It is designed for database administrators who primarily work over SSH on Linux servers or from terminal applications on their local machines, where graphical database tools are unavailable, impractical, or unnecessary.

The project focuses on reducing repetitive work while preserving the flexibility and power of the MySQL ecosystem.

---

# Vision Statement

To become the preferred terminal-based productivity tool for MySQL DBAs by combining the efficiency of command-line tools with the convenience of modern database browsers, while remaining lightweight, transparent, and familiar.

---

# Target Users

The primary audience is professional MySQL DBAs.

Typical environments include:

- AWS Aurora MySQL
- Oracle MySQL
- Percona Server
- Percona XtraDB Cluster (PXC)

The tool is also expected to be useful for:

- DevOps engineers
- Backend developers
- BI engineers
- Support engineers

who regularly interact with MySQL from the command line.

---

# Problem Statement

Traditional terminal tools are extremely powerful but require significant manual effort for routine administrative tasks.

Typical examples include:

- Repeated execution of metadata queries.
- Browsing database objects using multiple `SHOW` statements.
- Looking up information in `information_schema` or `performance_schema`.
- Viewing long DDL statements.
- Reading large stored procedures.
- Managing wide query result sets.
- Exporting query results.
- Monitoring server activity.

These tasks require unnecessary typing and context switching, slowing down daily operational work.

---

# Project Goals

The project aims to:

- Minimize repetitive typing.
- Reduce context switching.
- Provide fast access to metadata.
- Improve readability of SQL and server information.
- Preserve the workflow familiar to MySQL users.
- Remain fully keyboard-driven.
- Support secure production environments.
- Support offline deployment.

---

# What mydba Is

`mydba` is:

- A terminal user interface.
- A productivity tool.
- A metadata browser.
- A SQL workspace.
- A lightweight monitoring tool.
- A MySQL administration assistant.

---

# What mydba Is Not

`mydba` is not:

- A replacement for the MySQL client.
- A replacement for MySQL Shell.
- A graphical administration tool.
- A monitoring platform.
- An automation framework.
- An ORM.
- A migration tool.

---

# Design Philosophy

The application should feel like a natural extension of the existing MySQL ecosystem.

A DBA who already knows tools such as:

- mysql
- mysqlsh
- mysqldump

should immediately understand how to work with `mydba` without learning a completely new workflow.

---

# Long-Term Vision

The long-term objective is to build a tool that allows experienced MySQL administrators to perform the majority of their daily operational work without leaving the terminal, while keeping the interaction intuitive, transparent, and consistent with established MySQL practices.