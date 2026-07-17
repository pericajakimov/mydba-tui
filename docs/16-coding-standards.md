# Coding Standards

## Purpose

This document defines the coding standards for the `mydba` project.

The primary goal is to produce code that is easy to read, easy to review, easy to maintain, and approachable for both experienced Python developers and MySQL DBAs who may not have a software engineering background.

Consistency is considered more important than personal coding preferences.

---

# Design Principles

The codebase should be:

- Simple
- Explicit
- Readable
- Modular
- Predictable
- Easy to debug

Whenever multiple implementations are possible, choose the one that is easiest to understand.

---

# Python Version

The project targets:

```
Python 3.12+
```

Language features should follow modern Python best practices while avoiding unnecessary complexity.

---

# Type Hints

Type hints are required throughout the project.

Example:

```python
def load_tables(schema: str) -> list[Table]:
    ...
```

Functions should always declare:

- Parameter types
- Return type

---

# Dataclasses

Simple data containers should use `dataclass`.

Example:

```python
@dataclass(slots=True)
class TableInfo:
    name: str
    rows: int
    data_size: int
```

Business logic should remain outside dataclasses whenever practical.

---

# Documentation

Public modules, classes and functions must contain Google-style docstrings.

Example:

```python
def connect(profile: Profile) -> Connection:
    """Open a database connection.

    Args:
        profile: Connection profile.

    Returns:
        Established database connection.
    """
```

Private helper functions may omit docstrings when their purpose is obvious.

---

# Naming Conventions

Use descriptive names.

Examples:

Good:

```python
load_table_metadata()

render_json()

calculate_fragmentation()
```

Avoid abbreviations unless they are universally understood.

Bad:

```python
ltm()

doStuff()

calc()
```

---

# Variables

Variable names should clearly describe their purpose.

Examples:

```python
connection
selected_table
result_rows
fragmentation_percent
```

Avoid meaningless names such as:

```python
x
tmp
obj
foo
```

unless used as very short-lived loop variables.

---

# Constants

Constants should use uppercase.

Example:

```python
DEFAULT_PAGE_SIZE = 100

DEFAULT_REFRESH_INTERVAL = 3
```

Magic numbers should be avoided.

---

# Imports

Imports should be grouped as follows:

1. Standard library
2. Third-party packages
3. Project modules

Example:

```python
from pathlib import Path

from textual.app import App

from mydba_tui.connection import ConnectionManager
```

Avoid wildcard imports.

---

# Functions

Functions should do one thing.

If a function requires extensive comments to explain what it does, it is probably too large.

Prefer many small functions over one very large function.

---

# Classes

Classes should represent cohesive responsibilities.

Large "god objects" should be avoided.

A class should have one primary purpose.

---

# Module Organization

Each module should contain closely related functionality.

Avoid modules containing unrelated utility functions.

Typical module size should remain manageable.

---

# Separation of Responsibilities

The following responsibilities should remain separate:

- UI
- Business logic
- SQL execution
- Rendering
- Export
- Configuration

Mixing responsibilities should be avoided.

---

# SQL

Whenever practical, SQL statements should be stored in dedicated `.sql` files.

Example:

```
sql/browser/table_info.sql
```

Python code should load SQL from these files rather than embedding long SQL strings.

Dynamic SQL should only be generated when required.

---

# SQL Logging

Every SQL statement executed against the server must be written to the SQL log.

The SQL log contains:

- SQL text
- Timestamp
- Execution duration

The SQL log intentionally contains nothing else.

---

# Error Handling

Errors should be handled explicitly.

Avoid broad exception handling.

Preferred:

```python
except DatabaseError:
```

Avoid:

```python
except Exception:
```

unless re-raising after logging or during application shutdown.

---

# Logging

Application logging should use the standard logging framework.

Do not use:

```python
print()
```

for debugging.

Application logs and SQL logs are intentionally separate.

---

# Comments

Code should explain itself whenever possible.

Comments should explain:

- Why something is done.

Comments should not explain:

- What obvious code already says.

Good:

```python
# Aurora reports replica lag differently than traditional MySQL.
```

Bad:

```python
# Increment counter.
counter += 1
```

---

# Formatting

The project should use automated formatting.

Developers should avoid manual formatting discussions.

Formatting tools should be part of the development workflow.

---

# Static Analysis

The project should use static analysis tools throughout development.

The goal is to detect issues before runtime while maintaining readable code.

---

# Testing

Business logic should be testable independently of the UI.

Where practical:

- Database access
- Rendering
- Export
- Monitoring

should be implemented in a way that allows isolated testing.

---

# Performance

Optimize only after measuring.

Prefer readable implementations unless profiling demonstrates a clear need for optimization.

---

# Dependencies

Keep third-party dependencies to a minimum.

Before adding a new dependency, consider:

- Is it actively maintained?
- Does it solve a real problem?
- Can the same functionality be implemented simply within the project?

Every dependency increases maintenance cost.

---

# Backwards Compatibility

Public interfaces should remain stable whenever practical.

Breaking changes should be introduced deliberately and documented clearly.

---

# Design Philosophy

The project follows a pragmatic approach.

Code should be understandable by:

- Python developers
- MySQL DBAs
- Future contributors

Readability and maintainability always take precedence over clever implementations.

---

# Design Principles

The coding standards follow these principles:

- Readability first.
- Explicit over implicit.
- Small focused modules.
- Clear separation of responsibilities.
- Strong typing.
- Consistent formatting.
- Minimal dependencies.
- Easy long-term maintenance.
