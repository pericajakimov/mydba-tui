# Contributing to mydba

First of all, thank you for your interest in contributing to **mydba**.

The project started from a very practical goal:

> Build the best terminal-based MySQL administration tool for professional DBAs.

We welcome contributions that support this vision while keeping the project simple, maintainable, and focused.

---

# Project Philosophy

Before contributing, please read the documentation in the `docs/` directory.

In particular:

```
docs/
    00-vision.md
    01-philosophy.md
    02-architecture.md
    03-ui-principles.md
    16-coding-standards.md
    17-roadmap.md
```

These documents describe the project's long-term direction and design philosophy.

---

# Guiding Principles

Every contribution should follow these principles:

- Solve a real DBA problem.
- Keep the UI simple.
- Prefer keyboard-first interaction.
- Preserve SQL transparency.
- Avoid unnecessary dependencies.
- Favor readability over cleverness.
- Maintain compatibility with existing architecture.

If a proposed feature complicates the application without significantly improving the DBA workflow, it is unlikely to be accepted.

---

# Development Workflow

The preferred workflow is:

1. Discuss the idea (if it is a significant change).
2. Update the relevant documentation if the design changes.
3. Implement the feature.
4. Add or update tests where appropriate.
5. Submit a pull request.

For architectural changes, documentation should be updated before or alongside the implementation.

---

# Before Opening a Pull Request

Please ensure that:

- The code follows the project's coding standards.
- Type hints are included.
- Public APIs have Google-style docstrings.
- Formatting tools have been run.
- Static analysis passes.
- Existing functionality is not broken.
- Documentation is updated if needed.

Small, focused pull requests are preferred over large unrelated changes.

---

# Coding Style

The project uses:

- Python 3.12+
- Type hints throughout the codebase.
- `dataclass` for simple data models.
- Google-style docstrings.
- Clear module boundaries.
- Minimal external dependencies.

Refer to `docs/16-coding-standards.md` for complete details.

---

# SQL Guidelines

`mydba` follows a SQL-first architecture.

Whenever practical:

- Store SQL in dedicated `.sql` files.
- Keep SQL readable and well formatted.
- Use parameter binding for user input.
- Avoid embedding long SQL statements directly in Python code.

All SQL executed by the application is logged for transparency.

---

# User Interface

The UI should remain:

- Keyboard-first.
- Consistent.
- Easy to discover.
- Focused on DBA workflows.

Avoid introducing hidden shortcuts or inconsistent navigation.

Every new screen should expose its available actions clearly.

---

# Documentation

Documentation is considered part of the project source code.

If a contribution changes:

- Architecture
- Navigation
- User workflows
- Configuration
- Plugin interfaces

the corresponding documentation should be updated.

New architectural decisions should also be recorded as an ADR or in the Decision Log when appropriate.

---

# Scope

The project intentionally focuses on interactive MySQL administration.

Please avoid features that move the project toward:

- A full IDE
- An automation framework
- A deployment tool
- A monitoring platform
- A schema migration framework

Those are valuable projects, but they are outside the scope of `mydba`.

---

# Dependencies

New dependencies should be introduced only when they provide significant value.

Before proposing one, consider:

- Is it actively maintained?
- Is it widely used?
- Does it simplify the project?
- Can the functionality be implemented reasonably without it?

Every dependency increases long-term maintenance.

---

# Pull Requests

Good pull requests are:

- Small
- Focused
- Well documented
- Easy to review

If a pull request contains multiple unrelated changes, it may be requested to split them into separate submissions.

---

# Bug Reports

When reporting bugs, please include as much relevant information as possible:

- `mydba` version
- Python version
- Operating system
- MySQL server type
- MySQL version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant log excerpts (if applicable)

---

# Feature Requests

Feature requests are welcome.

The most useful requests describe:

- The DBA problem being solved.
- The current workflow.
- Why the existing behavior is insufficient.
- The expected improvement.

Real-world use cases are preferred over hypothetical scenarios.

---

# Code of Conduct

Please be respectful and constructive.

The goal is to build a high-quality tool through thoughtful technical discussions.

Disagreements are expected, but they should always focus on the technical merits of an idea rather than on individuals.

---

# License

The project's license has not yet been finalized.

Until a license is selected, please assume that contributions are intended for inclusion in the project under the future project license.

---

# Final Notes

The long-term success of `mydba` depends more on consistency than on the number of features.

When in doubt, choose the solution that is:

- Simpler
- Clearer
- Easier to maintain
- Better aligned with the needs of professional MySQL DBAs

Thank you for helping make **mydba** a better tool.
