# Developer Guide

## Purpose

This document explains how to contribute to the `mydba` project and describes the overall development workflow.

Although the initial development is led by the project maintainer, the architecture is intentionally designed so that future contributors can understand the project quickly and begin working with minimal onboarding.

This document focuses on *how the project is developed*, not *how the application is used*.

---

# Project Philosophy

When contributing to `mydba`, always remember the project's primary goal:

> Build the best terminal-based MySQL administration tool for professional MySQL DBAs.

Every design decision should support this objective.

If a feature makes the application more complicated without significantly improving the DBA workflow, it should probably not be implemented.

---

# Core Principles

The project follows several fundamental principles:

- Simplicity over cleverness.
- Readability over brevity.
- Explicit behavior over hidden magic.
- SQL transparency.
- Keyboard-first interaction.
- Metadata-first navigation.
- Minimal dependencies.
- Long-term maintainability.

---

# Know the User

The primary users are experienced MySQL DBAs.

Typical characteristics:

- Comfortable working in terminals.
- Use SSH daily.
- Already know the MySQL ecosystem.
- Prefer keyboard navigation.
- Value speed and predictability.

The application is **not** intended to teach MySQL.

It is intended to make experienced DBAs more productive.

---

# Project Structure

The repository is organized by responsibility.

Typical top-level directories include:

```
docs/
src/
tests/
sql/
themes/
scripts/
```

Each directory should have a clearly defined purpose.

Avoid creating miscellaneous folders.

---

# Before Writing Code

Before implementing a feature:

1. Read the relevant design document.
2. Check the Decision Log.
3. Verify that the feature aligns with the project philosophy.
4. Keep the implementation as simple as possible.

Architecture decisions should be made before implementation, not during coding.

---

# Documentation First

Documentation is considered part of the source code.

Significant architectural changes should be documented before implementation begins.

Relevant documents should be updated whenever a design decision changes.

---

# Coding Standards

All code must follow the project's coding standards.

In particular:

- Type hints everywhere.
- Dataclasses where appropriate.
- Google-style docstrings.
- Small focused modules.
- Clear naming.
- Strong separation of responsibilities.

Refer to `docs/16-coding-standards.md` for detailed guidance.

---

# SQL Organization

Long SQL statements should not be embedded directly in Python code.

Instead:

- Store SQL in dedicated `.sql` files.
- Load SQL when required.
- Keep SQL readable and properly formatted.

This makes SQL easier for DBAs to review and optimize.

---

# SQL Transparency

Every SQL statement executed by the application must be visible in the SQL log.

This includes:

- Metadata queries
- Monitoring queries
- Administrative queries
- User queries

Hidden SQL is contrary to the philosophy of the project.

---

# User Interface

The UI should remain:

- Clean
- Predictable
- Keyboard-driven
- Easy to navigate

Users should never need to memorize navigation.

Every screen should clearly display the available actions.

---

# Feature Design

When proposing a new feature, ask:

- Does this solve a real DBA problem?
- Is it something a DBA performs frequently?
- Can it be implemented without increasing complexity?
- Does it fit naturally into the existing workflow?

Features that fail these questions should be reconsidered.

---

# Performance

Performance matters, but only after correctness.

Prefer:

Correct → Readable → Fast

over

Fast → Complex

Optimize only after measuring.

---

# Dependencies

Adding a dependency is a long-term commitment.

Before introducing one, consider:

- Is it actively maintained?
- Is it widely used?
- Does it solve a significant problem?
- Can the functionality be implemented reasonably within the project?

Prefer fewer dependencies whenever practical.

---

# Error Handling

Errors should be:

- Explicit
- Actionable
- Understandable

Database errors should generally be presented as returned by MySQL.

The application should avoid hiding useful diagnostic information.

---

# Logging

Two independent logging systems exist:

## SQL Log

Contains only SQL statements executed against the server.

Purpose:

- Transparency
- Debugging
- Query optimization

## Application Log

Contains:

- Internal errors
- Debug messages
- Exceptions
- Startup and shutdown information

Application logs must never contain passwords.

---

# Testing

Whenever practical:

- Business logic
- Rendering
- Exporters
- Monitoring
- SQL generation

should be testable independently of the user interface.

Avoid tightly coupling business logic to the TUI.

---

# Backwards Compatibility

Existing behavior should remain stable whenever possible.

Breaking changes should be deliberate and documented.

If a breaking architectural change is necessary:

1. Update the Decision Log.
2. Update the relevant design documents.
3. Explain the migration path.

---

# Future Contributors

Future contributors should feel comfortable extending the project without needing to understand every internal implementation detail.

Well-defined interfaces and clear module boundaries are preferred over implicit coupling.

---

# What Not To Build

Avoid turning `mydba` into:

- A general IDE
- An automation framework
- A monitoring platform
- A deployment tool
- A schema migration framework

The project should remain focused on interactive database administration.

---

# Communication

Architectural discussions should always consider:

- Simplicity
- Consistency
- Existing design principles
- Long-term maintenance

When in doubt, choose the simpler solution.

---

# Development Workflow

Recommended workflow:

```
Read Documentation

        ↓

Discuss Design

        ↓

Update Documentation

        ↓

Implement Feature

        ↓

Test

        ↓

Review

        ↓

Merge
```

This order helps keep implementation aligned with the documented architecture.

---

# Long-Term Goal

The project should remain understandable years after its initial implementation.

Future developers should be able to read the documentation, understand the architecture, and contribute confidently without needing extensive historical context.

---

# Design Principles

The Developer Guide follows these principles:

- Documentation first.
- Simplicity over complexity.
- SQL transparency.
- Readability first.
- Strong separation of responsibilities.
- DBA-focused design.
- Maintainability over cleverness.
- Consistent development practices.
