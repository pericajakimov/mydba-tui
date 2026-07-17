# ADR-0001: Project Naming

- **Status:** Accepted
- **Date:** 2026-07-17

---

# Context

During the initial design phase, several names were considered for the project.

The project needed three separate names:

- Git repository
- Python package
- End-user executable

The name should satisfy several goals:

- Short and memorable
- Clearly related to MySQL administration
- Suitable for open-source publication
- Compatible with Python package naming conventions
- Compatible with command-line usage
- Consistent across documentation

---

# Decision

The project uses the following names:

| Component | Name |
|-----------|------|
| Repository | **mydba-tui** |
| Python package | **mydba_tui** |
| Executable | **mydba** |

---

# Rationale

The repository name includes **-tui** because it clearly identifies the project as a terminal user interface application.

The Python package follows standard Python naming conventions by using underscores instead of hyphens.

The executable remains simply:

```
mydba
```

This is intentionally short because it will be typed frequently by users.

---

# Alternatives Considered

## mysql-inspector

Rejected.

Although descriptive, it is unnecessarily long for a command-line tool.

---

## mysql-browser

Rejected.

The application is significantly more than an object browser.

---

## mysql-admin

Rejected.

Too generic and easily confused with existing MySQL utilities.

---

## aurora-specific naming

Rejected.

The application is intentionally designed as a MySQL administration tool rather than an Aurora-specific tool.

Aurora support is implemented through automatic backend detection.

---

# Consequences

The following conventions are used consistently throughout the project:

Repository:

```
mydba-tui
```

Python imports:

```python
import mydba_tui
```

Executable:

```bash
mydba
```

Example usage:

```bash
mydba

mydba -h db.example.com

mydba -u admin
```

---

# Future Considerations

The chosen naming allows future expansion without affecting existing users.

Additional packages, plugins, or companion tools may use the `mydba` prefix while preserving a consistent naming scheme.