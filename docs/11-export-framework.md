# Export Framework

## Purpose

The Export Framework provides a modular mechanism for exporting query results from `mydba`.

The framework is designed to support both small interactive exports and large data extraction jobs while remaining independent from the SQL execution engine.

The initial goal is to support the export formats most commonly used by MySQL DBAs, while making it easy to add new exporters in future versions.

---

# Design Goals

The Export Framework should:

- Be modular.
- Support streaming exports.
- Support large result sets.
- Minimize memory usage.
- Integrate naturally with the SQL Workspace.
- Allow future exporters to be added without modifying existing code.

---

# Design Philosophy

Exporting data is considered an optional action performed after or during query execution.

The framework should support two different workflows:

1. Export an already displayed result set.
2. Execute a query directly into an export file.

Each workflow has different performance characteristics and should be implemented separately.

---

# Supported Export Formats

The initial version supports:

- CSV
- TSV
- SQL INSERT
- JSONL

Additional exporters may be added later.

Examples include:

- XML
- Markdown
- HTML
- Excel
- Apache Parquet

---

# Export Workflows

## Interactive Export

Workflow:

```
Write Query
      ↓
Execute
      ↓
Review Result
      ↓
Export
      ↓
Choose Format
      ↓
Choose Destination
      ↓
Write File
```

This workflow is intended for small and medium-sized result sets.

---

## Direct Export

Workflow:

```
Write Query
      ↓
Choose Export
      ↓
Choose Format
      ↓
Choose Destination
      ↓
Execute Query
      ↓
Stream Rows Directly To File
```

Rows are not rendered in the SQL Workspace.

Instead, the workspace displays:

- Execution progress
- Rows exported
- Execution time
- Output file location

This workflow is intended for large exports.

---

# File Selection

During export, the user is prompted for the destination file.

The initial implementation uses a simple path prompt.

A graphical file browser is not required.

---

# Existing Files

Existing files should **not** be overwritten automatically.

If the selected file already exists, the export is cancelled and the user is prompted to choose another filename.

This reduces the risk of accidental data loss.

---

# Progress Reporting

Long-running exports should display progress whenever possible.

Examples include:

- Rows written
- Elapsed time
- Export status

Progress reporting should remain lightweight and must not significantly impact export performance.

---

# Streaming

Large exports should stream rows directly from the database cursor to the output file.

The framework should avoid loading the entire result set into memory.

This allows exports of arbitrarily large datasets.

---

# Export Interface

Each exporter implements a common interface.

Example:

```
Exporter

    initialize()

    write_header()

    write_row()

    finalize()
```

The SQL execution engine should interact only with this common interface.

---

# CSV Exporter

Characteristics:

- Delimited by commas.
- Configurable quoting.
- UTF-8 encoding.
- One row per line.

---

# TSV Exporter

Characteristics:

- Tab-delimited.
- UTF-8 encoding.
- One row per line.

Suitable for direct loading into spreadsheets or command-line tools.

---

# SQL INSERT Exporter

Generates SQL INSERT statements.

Example:

```sql
INSERT INTO table_name
VALUES (...);

INSERT INTO table_name
VALUES (...);
```

The generated SQL should resemble the style produced by standard MySQL utilities.

---

# JSONL Exporter

Produces one JSON document per line.

Example:

```json
{"id":1,"name":"Alice"}
{"id":2,"name":"Bob"}
```

JSONL is particularly useful for downstream processing and log-style ingestion.

---

# Character Encoding

The default export encoding is:

```
UTF-8
```

Future versions may allow additional encodings through exporter configuration.

---

# Compression

Compression is intentionally **not** included in the initial implementation.

Future versions may support:

- gzip
- bzip2
- xz
- zstd
- User-defined compression pipelines

The export architecture should make this extension straightforward.

---

# Clipboard Support

Clipboard export is intentionally excluded from the initial version.

The primary target environment is SSH over terminal, where clipboard integration is less useful and often platform-dependent.

---

# Error Handling

If an export fails:

- Stop the export.
- Close the output file safely.
- Display the error.
- Preserve any successfully written data.

The framework should never silently ignore write errors.

---

# SQL Transparency

The Export Framework does not modify the SQL statement being executed.

The original SQL is written to the SQL log exactly as executed.

The export mechanism affects only the destination of the result set.

---

# Extensibility

Adding a new exporter should require:

1. Implementing the exporter interface.
2. Registering the exporter.
3. Providing a display name and file extension.

No changes should be required elsewhere in the application.

---

# Design Principles

The Export Framework follows these principles:

- Streaming over buffering.
- Predictable behavior.
- No accidental overwrites.
- SQL transparency.
- Modular architecture.
- Efficient handling of large result sets.
- Easy future extensibility.
