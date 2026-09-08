# Changelog

All notable changes to **mydba** will be documented in this file.

The project follows the principles of **Keep a Changelog** and **Semantic Versioning**.

---

## [Unreleased]

### Added

#### Connection Manager

- Connection profiles with environment grouping and backend/vendor detection.
- Credential resolution from profile fields, `.mylogin.cnf` login paths, and
  `.my.cnf` option files.
- SSL and SSH tunnel support.
- Reconnect action (`X` in the Object Browser, `Ctrl+Shift+X` in the SQL
  Workspace). Closes the existing connection and SSH tunnel, re-establishes a
  fresh MySQL session against the current profile, and reloads all metadata.
- Same-endpoint reconnect preserves the SQL Workspace session (editor + log);
  switching to a different profile endpoint rotates the session log and clears
  the editor and results.

#### Object Browser

- Metadata browsing for schemas, tables, views, procedures, functions, events,
  and triggers.
- Per-object tabs: General, Columns, Indexes, Partitions, Foreign Keys,
  Triggers, Grants, Dependencies, DDL, and Sample Data.
- Dependency Analysis Engine using sqlglot to parse procedural SQL and build a
  bidirectional dependency graph with foreign-key labels.

#### SQL Workspace

- Interactive SQL editor with a custom MySQL syntax highlighter covering
  procedural SQL.
- Query execution with typed, colored result output and JSON highlighting.
- EXPLAIN, EXPLAIN FORMAT=JSON, and EXPLAIN ANALYZE.
- Vertical (`\G`) output, horizontal scrolling, and a configurable row display
  limit.
- Session log with owner-only permissions, human-readable durations, and
  save-to-file support.
- Context-aware autocomplete (statement starters, schema objects, and columns
  after a dot), triggered by typing.
- SQL formatter (`Ctrl+Shift+F`) built on sqlglot with configurable rules.

#### Export Framework

- Pluggable, auto-discovered exporters: CSV, CSV (semicolon), TSV,
  SQL INSERT, SQL INSERT (batch), JSONL, JSON, XML, HTML, and Markdown.
- Interactive export (`Ctrl+E`) of the last result set.
- Direct export (`Ctrl+Shift+E`) that streams query results straight to a file.

#### Configuration

- Documented `settings.yaml` with human-readable durations.

#### Tooling

- `make all` target that runs format, lint, typecheck, test, then the app.

#### Foundation

- Textual TUI application shell, theme support, application and SQL logging,
  and the configuration framework.
- Project documentation set (`docs/`), ADRs, and contribution guidelines.

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
