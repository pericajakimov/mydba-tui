# Changelog

All notable changes to **mydba** will be documented in this file.

The project follows the principles of **Keep a Changelog** and **Semantic Versioning**.

---

## [Unreleased]

### Added

#### Connection

- Reconnect action (`X` in the Object Browser, `Ctrl+Shift+X` in the SQL
  Workspace). Closes the existing connection and SSH tunnel, re-establishes a
  fresh MySQL session against the current profile, and reloads all metadata.
- Same-endpoint reconnect preserves the SQL Workspace session (editor + log);
  switching to a different profile endpoint rotates the session log and clears
  the editor and results.

#### Repository

- Initial repository structure.
- Bootstrap documentation.
- Architecture documentation.
- Developer documentation.
- Contribution guidelines.
- Initial ADRs.

#### Project Vision

- Defined long-term vision.
- Established project philosophy.
- Defined design principles.
- Documented roadmap.

#### Architecture

- Defined modular architecture.
- Established SQL-first architecture.
- Established plugin architecture.
- Defined packaging strategy.
- Defined configuration strategy.
- Defined coding standards.

#### User Interface

- Defined keyboard-first navigation.
- Defined metadata-first Object Browser.
- Defined SQL Workspace.
- Defined rendering strategy.
- Defined Monitoring page.
- Defined Administration pages.
- Defined Export Framework.
- Defined connection management.

#### Development

- Defined repository naming.
- Defined package naming.
- Defined executable naming.
- Established development workflow.
- Selected Python 3.12+.
- Adopted type hints.
- Adopted dataclasses.
- Adopted Google-style docstrings.

#### Logging

- Defined application logging.
- Defined SQL logging.
- Established SQL transparency as a core design principle.

#### Documentation

Added the following project documentation:

```
README.md

CONTRIBUTING.md

ROADMAP.md

CHANGELOG.md

docs/
    00-vision.md
    01-philosophy.md
    02-architecture.md
    03-ui-principles.md
    04-navigation.md
    05-connection-manager.md
    06-object-browser.md
    07-administration.md
    08-sql-workspace.md
    09-rendering.md
    10-monitoring.md
    11-export-framework.md
    12-security.md
    13-configuration.md
    14-packaging.md
    15-plugin-architecture.md
    16-coding-standards.md
    17-roadmap.md
    18-decision-log.md
    19-developer-guide.md

adr/
    ADR-0001-project-name.md
    ADR-0002-one-process-one-connection.md
    ADR-0003-metadata-first.md
    ADR-0004-transparent-sql.md
    ADR-0005-keyboard-first.md
    ADR-0006-one-endpoint-per-profile.md
    ADR-0007-sql-first.md
```

---

## [0.1.0] - Planned

### Added

- Initial application skeleton.
- Basic Textual application.
- Theme framework.
- Logging framework.
- Configuration framework.
- Connection framework.

---

## [0.2.0] - Planned

### Added

- Connection Manager.
- Connection profiles.
- Environment grouping.
- Backend detection.
- SSL support.
- SSH tunnel support.

---

## [0.3.0] - Planned

### Added

- Object Browser.
- Schema Browser.
- DDL viewer.
- Dependencies.
- Grants.
- Sample data.

---

## [0.4.0] - Planned

### Added

- SQL Workspace.
- Syntax highlighting.
- Query execution.
- Vertical output.
- JSON rendering.
- EXPLAIN support.

---

## [0.5.0] - Planned

### Added

- Administration module.
- Process List.
- Users.
- Replication.
- Variables.
- Status.
- Locks.
- Transactions.

---

## [0.6.0] - Planned

### Added

- Monitoring page.
- Server overview.
- Live metrics.
- Lightweight graphs.

---

## [0.7.0] - Planned

### Added

- Export Framework.
- CSV exporter.
- TSV exporter.
- SQL INSERT exporter.
- JSONL exporter.

---

## [0.8.0] - Planned

### Added

- UI refinements.
- Performance improvements.
- Additional themes.
- Configuration enhancements.

---

## [1.0.0] - Planned

### Added

- First stable release.
- Complete documentation.
- Stable plugin interface.
- Offline installation.
- Cross-platform support.
- Production-ready workflows.

---

## Versioning

The project follows Semantic Versioning:

```
MAJOR.MINOR.PATCH
```

- **MAJOR** — Breaking architectural or API changes.
- **MINOR** — New functionality with backwards compatibility.
- **PATCH** — Bug fixes and minor improvements.

---

## Release Philosophy

Releases should be:

- Small
- Stable
- Well documented
- Fully tested

Every release should provide meaningful improvements while preserving the project's core philosophy of simplicity, transparency, and productivity for professional MySQL DBAs.
