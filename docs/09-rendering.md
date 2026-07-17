# Rendering

## Purpose

The Rendering subsystem is responsible for presenting information in a readable, consistent and terminal-friendly format.

Rendering is a core part of the user experience. The goal is not simply to print text, but to make complex database information easy to understand while working over SSH.

The rendering subsystem is independent from data retrieval. Its only responsibility is to transform already available data into a visual representation.

---

# Design Goals

The renderer should:

- Maximize readability.
- Minimize visual noise.
- Use colors consistently.
- Handle large objects gracefully.
- Support narrow terminals.
- Preserve performance.
- Remain predictable across the application.

---

# General Principles

Rendering should emphasize information, not decoration.

Visual elements must have meaning.

Examples include:

- Colors
- Alignment
- Indentation
- Grouping
- Borders
- Spacing

The same type of information should always be rendered the same way.

---

# Rendering Types

The renderer supports multiple output types.

These include:

- SQL
- DDL
- JSON
- Result tables
- Vertical output
- Metadata tables
- Trees
- Monitoring widgets
- Status panels

Each renderer has a dedicated implementation but follows the same visual guidelines.

---

# SQL Rendering

SQL displayed by the application should be:

- Syntax highlighted.
- Properly indented.
- Easy to scan.
- Scrollable.

Keywords should be visually distinct from identifiers and literals.

The formatting should resemble professionally formatted SQL rather than the raw output returned by MySQL.

---

# DDL Rendering

DDL uses the same syntax highlighting rules as SQL.

Long statements should remain readable without requiring horizontal scrolling whenever possible.

Objects such as:

- Tables
- Views
- Procedures
- Functions
- Events
- Triggers

all use the same renderer.

---

# JSON Rendering

JSON should always be formatted before display.

Requirements:

- Proper indentation.
- Syntax highlighting.
- Stable key ordering (when preserving the original order is not required).
- Scrollable output.

The renderer should make deeply nested JSON easy to inspect.

---

# Result Tables

The default presentation for query results is a tabular view.

Requirements:

- Column headers.
- Automatic column sizing where practical.
- Horizontal scrolling.
- Vertical scrolling.
- Stable alignment.

Numeric values should be right-aligned.

Text values should be left-aligned.

NULL values should be visually distinguishable.

---

# Vertical Output

The renderer supports a vertical presentation similar to the MySQL client's `\G` format.

Example:

```
*************************** 1. row ***************************

             id: 123
           name: Customer A
         status: ACTIVE
```

Requirements:

- Field names right-aligned.
- Values aligned after the separator.
- JSON values automatically formatted.
- Long values wrapped cleanly.
- Easy keyboard scrolling.

Vertical output is recommended for:

- Wide tables.
- JSON documents.
- Individual record inspection.

---

# Metadata Tables

Metadata views should prioritize readability over completeness.

Examples include:

- Columns
- Indexes
- Partitions
- Variables
- Status
- Users

Only the most useful information should be displayed by default.

Additional details remain available through dedicated views such as DDL.

---

# Tree Rendering

Hierarchical structures are displayed using a tree renderer.

Examples include:

- Object Browser
- Dependency graphs
- Schema navigation

Tree rendering should remain compact while clearly indicating parent-child relationships.

---

# Dependency Rendering

Dependencies should distinguish between:

Incoming dependencies

Examples:

- Tables referencing this table.

Outgoing dependencies

Examples:

- Procedures using the table.
- Views using the table.
- Functions using the table.

The presentation should make object relationships easy to understand.

---

# Monitoring Widgets

Monitoring information should be visually lightweight.

Simple line graphs are preferred.

The objective is operational awareness rather than detailed performance analysis.

Typical widgets include:

- Connections
- Queries per second
- InnoDB reads
- InnoDB writes
- Replication lag

---

# Status Indicators

Status values should use consistent colors.

Suggested meanings:

- Green → Healthy
- Yellow → Warning
- Orange → Attention required
- Red → Critical
- Gray → Informational

Color should supplement text rather than replace it.

---

# Environment Colors

Environment colors are defined by the connection profile.

Recommended mapping:

| Environment | Color |
|-------------|-------|
| Production | Red |
| Stage | Orange |
| QA | Blue |
| Development | Green |

The current environment remains visible in the application header.

---

# SQL Transparency

The renderer must never modify SQL statements in a way that changes their meaning.

Formatting affects presentation only.

The SQL log always contains the original executed SQL.

---

# Performance

Rendering should remain efficient.

The renderer should avoid unnecessary recomputation while scrolling or navigating.

Large result sets should be rendered incrementally whenever practical.

---

# Accessibility

The renderer should not rely solely on color.

Information should remain understandable on monochrome terminals or when using custom color themes.

Alignment, spacing and formatting must continue to communicate structure even without colors.

---

# Theme Support

Rendering should be theme-aware.

Themes may customize:

- Colors
- Highlight styles
- Borders
- Selected items
- Status colors

Rendering behavior itself remains identical across themes.

---

# Design Principles

The Rendering subsystem follows these principles:

- Readability first.
- Consistency everywhere.
- Colors with meaning.
- Excellent support for SQL and JSON.
- Efficient rendering.
- Familiar terminal appearance.
- Predictable presentation.
