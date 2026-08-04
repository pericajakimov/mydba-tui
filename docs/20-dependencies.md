# Dependency Analysis Engine

## Purpose

The Dependency Analysis Engine provides accurate dependency information between MySQL database objects.

Unlike simple text searches, this engine understands SQL syntax, object naming rules, and schema resolution in order to produce reliable dependency information.

The primary goal is to answer questions such as:

- Which views reference this table?
- Which stored procedures update this table?
- Which triggers call this function?
- Which events execute this procedure?
- What objects will be affected if this table is modified or dropped?

The dependency engine should become the foundation for future features such as:

- Impact Analysis
- Safe DROP / ALTER validation
- Dependency Graph visualization
- Object lineage
- Schema comparison

---

# Design Principles

The implementation follows these principles:

- Never rely on simple string matching or regular expressions.
- Parse SQL using a proper SQL parser.
- Normalize all object references into fully-qualified names.
- Build an in-memory dependency graph.
- Separate parsing, name resolution and dependency storage into independent components.
- Make the implementation parser-independent so another parser can be adopted in the future.

---

# Supported Object Types

The dependency engine analyzes relationships between:

- Tables
- Views
- Triggers
- Stored Procedures
- Functions
- Events

Foreign key relationships are handled separately through metadata and also appear in dependency information.

---

# Object Enumeration

All database objects are first discovered from metadata.

Sources:

- INFORMATION_SCHEMA.TABLES
- INFORMATION_SCHEMA.VIEWS
- INFORMATION_SCHEMA.ROUTINES
- INFORMATION_SCHEMA.TRIGGERS
- INFORMATION_SCHEMA.EVENTS
- INFORMATION_SCHEMA.KEY_COLUMN_USAGE

The parser never attempts to discover objects by scanning SQL text.

---

# SQL Parsing

Each object's SQL definition is parsed into an Abstract Syntax Tree (AST).

The parser identifies references to:

- Tables
- Views
- Routines (procedures and functions)
- Events (where applicable)

The parser correctly handles:

- Quoted identifiers
- Nested queries
- Joins
- Aliases
- CTEs
- Subqueries
- UNION
- INSERT ... SELECT
- UPDATE
- DELETE
- BEGIN/END blocks (procedure, trigger, event bodies)
- Nested BEGIN/END (handler blocks, nested cursor blocks)
- IF/ELSEIF/ELSE/END IF flow control
- WHILE/LOOP/REPEAT control flow
- CASE/WHEN/END CASE
- DECLARE CURSOR FOR (extracts the SELECT inside)
- CALL statements (procedure invocations)
- Function calls in expressions (user-defined functions)

The parser ignores:

- Comments
- String literals
- Aliases
- Formatting
- MySQL built-in functions (CONCAT, NOW, COUNT, etc.)
- Variable declarations (DECLARE var TYPE)
- SET variable assignments
- OPEN/CLOSE/FETCH cursor operations

---

# Parsing Context

The parser alone cannot determine the schema of unqualified object names.

Every parsing operation includes context describing the object currently being parsed.

Example:

Current object:

```
VIEW sales.active_orders
```

Parsing context:

```
Current Schema = sales
Object Type    = VIEW
Object Name    = active_orders
```

This context is required during name resolution.

---

# Name Resolution

After parsing, every discovered object reference is normalized into a fully-qualified name.

Example:

SQL:

```sql
SELECT *
FROM orders;
```

Raw parser output:

```
schema = NULL
table  = orders
```

Resolved reference:

```
sales.orders
```

because the current object belongs to the `sales` schema.

---

Another example:

```sql
SELECT *
FROM archive.orders;
```

Parser output:

```
schema = archive
table  = orders
```

Resolved reference:

```
archive.orders
```

No schema substitution occurs because the SQL already specifies the schema explicitly.

---

# Canonical Object Names

Internally, every object has a canonical fully-qualified name.

Examples:

```
sales.orders
sales.customers
archive.orders
reporting.monthly_sales
```

The dependency engine never stores ambiguous object names such as:

```
orders
customers
```

All references are normalized immediately after parsing.

---

# Internal Object Model

The dependency engine identifies objects using unique fully-qualified references.

Object:

```
Type
Schema
Name
```

Dependencies are stored as:

```
Source (schema.name)
Target (schema.name)
Dependency Type
```

This simplifies graph traversal and avoids ambiguity.

---

# Dependency Types

Examples:

```
View       → Table
View       → View
Procedure  → Table
Procedure  → Procedure
Procedure  → Function
Trigger    → Table
Trigger    → Procedure
Trigger    → Function
Event      → Procedure
Event      → Table
ForeignKey → Table
```

The implementation allows new dependency types to be added later.

---

# Dependency Graph

The final output is an in-memory graph.

Example:

```
EVENT nightly_cleanup
        │
        ▼
PROCEDURE archive_orders
        │
        ▼
TABLE orders
```

This graph allows:

- Direct dependency lookup
- Reverse dependency lookup
- Recursive dependency traversal
- Impact analysis

---

# Direct vs Indirect Dependencies

The UI distinguishes between direct and indirect references.

Example:

```
TABLE sales.orders

Direct:
    VIEW sales.active_orders
    PROCEDURE sales.archive_orders

Indirect:
    EVENT sales.nightly_cleanup
        → PROCEDURE sales.archive_orders
            → TABLE sales.orders
```

This provides more useful information than a flat list.

---

# Refresh Strategy

The dependency graph is not rebuilt every time a user opens the Dependencies tab.

Instead:

1. Enumerate database objects.
2. Parse each object's SQL definition.
3. Resolve names.
4. Build dependency graph.
5. Cache the graph in memory.

A single Refresh action in the Object Browser rebuilds both the object tree and the dependency cache.

Future optimization may support incremental refresh after DDL changes.

---

# Unsupported Scenarios

Some SQL cannot be analyzed statically.

Examples include dynamic SQL:

```sql
SET @sql = CONCAT('SELECT * FROM ', table_name);
PREPARE stmt FROM @sql;
```

In these cases the dependency engine:

- Continues parsing the remaining code.
- Reports that dynamic SQL was detected.
- Marks dependency information as potentially incomplete.

---

# Separation of Responsibilities

The implementation consists of clearly separated layers.

```
SQL Definition
      │
      ▼
SQL Parser (sqlglot)
      │
      ▼
Raw Object References
      │
      ▼
Name Resolver
      │
      ▼
Fully Qualified References
      │
      ▼
Dependency Graph
```

Each layer has a single responsibility.

---

# Future Enhancements

Possible extensions:

- Dependency Graph visualization
- Full dependency tree screen (dedicated screen showing the complete
  dependency tree for any object, with recursive traversal of direct
  and indirect dependencies, accessible from the Dependencies tab)
- Export dependency graph
- Circular dependency detection
- Safe DROP validation
- Safe ALTER validation
- Object lineage
- Cross-schema dependency browser
- Dependency search
- Reverse dependency search
- Incremental graph refresh
- Schema comparison using dependency graphs
- Auto-refresh after DDL (object browser and dependency cache should
  refresh automatically when a DDL statement is executed, e.g., CREATE,
  ALTER, DROP — detected via the SQL Workspace module)

---

# Non-Goals

The dependency engine is not intended to:

- Execute SQL
- Validate SQL correctness
- Rewrite SQL
- Interpret dynamic SQL
- Replace the MySQL optimizer

Its sole responsibility is to discover and maintain object dependencies.

---

# Summary

The Dependency Analysis Engine provides reliable dependency information by combining:

- SQL parsing (via sqlglot with MySQL dialect)
- Schema-aware name resolution
- Metadata lookup
- Graph-based dependency storage

This approach avoids the limitations of text searching, correctly handles schema-qualified names, supports multiple schemas containing identically named objects, and provides a solid foundation for future metadata analysis features throughout mydba.
