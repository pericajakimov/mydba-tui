# ADR-0007: SQL-First Architecture

- **Status:** Accepted
- **Date:** 2026-07-17

---

# Context

Many database applications generate SQL dynamically inside application code.

Typical examples include:

- Long SQL strings embedded in Python files.
- Complex string concatenation.
- Query builders.
- Object-relational mappers (ORMs).

While these approaches can reduce code duplication, they make it difficult for DBAs to:

- Read the SQL.
- Review execution plans.
- Optimize queries.
- Understand how the application works.

Because the primary users and future contributors to `mydba` are expected to have strong SQL knowledge, SQL should be treated as a first-class part of the project rather than an implementation detail.

---

# Decision

`mydba` adopts a **SQL-first architecture**.

Whenever practical, SQL statements are stored as standalone `.sql` files and loaded by the application at runtime.

Python is responsible for:

- Loading SQL.
- Binding parameters.
- Executing statements.
- Processing results.

SQL is responsible for retrieving data from the server.

---

# Rationale

Separating SQL from application logic provides several advantages:

- SQL is easier to read.
- DBAs can review queries without reading Python code.
- Queries can be tested independently.
- Formatting remains clean.
- Optimizations are easier to perform.
- SQL changes usually require no Python modifications.

The SQL becomes part of the project's public architecture rather than hidden implementation details.

---

# Directory Structure

SQL files are organized by functional area.

Example:

```
sql/

    browser/

        table_info.sql
        indexes.sql
        partitions.sql

    administration/

        processlist.sql
        replication.sql

    monitoring/

        server_load.sql
```

Each file should have a single responsibility.

---

# Dynamic SQL

Some SQL must be generated dynamically.

Examples include:

- Object names.
- Optional filters.
- ORDER BY clauses.
- LIMIT clauses.

Dynamic SQL should be kept to the minimum necessary.

Only the variable parts should be constructed programmatically.

The majority of the statement should remain in the SQL file.

---

# Parameter Binding

User values must always be supplied through parameter binding.

String concatenation must never be used for user-supplied values.

This improves:

- Security.
- Readability.
- Correctness.

---

# SQL Formatting

SQL files should follow a consistent formatting style.

General guidelines:

- Uppercase SQL keywords.
- One clause per line.
- Clear indentation.
- Logical grouping of joins and predicates.
- Meaningful aliases.

The SQL should be readable without additional formatting tools.

---

# SQL Ownership

SQL files are considered part of the project's public source code.

They should be reviewed with the same care as Python code.

Future contributors should feel comfortable improving SQL without needing to understand the surrounding application internals.

---

# SQL Logging

Every SQL statement executed from a `.sql` file is recorded in the SQL log.

This preserves the project's principle of SQL transparency regardless of where the statement originated.

---

# Alternatives Considered

## Embedded SQL Strings

Rejected.

Long embedded SQL quickly becomes difficult to read and maintain.

Changes often require editing Python code even when the application logic remains unchanged.

---

## ORM

Rejected.

The project is an administration tool, not a business application.

ORMs introduce unnecessary abstraction and make generated SQL harder to predict and optimize.

Professional DBAs generally prefer working directly with SQL.

---

## Query Builder Libraries

Rejected.

Although they reduce string concatenation, they also hide the final SQL behind another abstraction layer.

The project values explicit SQL over abstraction.

---

# Consequences

Developers should think in terms of SQL first and Python second.

When implementing a new feature:

1. Design the SQL.
2. Validate it against supported MySQL versions.
3. Store it in the appropriate `.sql` file.
4. Integrate it into the Python layer.

This workflow keeps SQL visible and maintainable.

---

# Exceptions

Small SQL statements may remain inline when they are trivial.

Examples include:

```sql
SELECT 1
```

```sql
USE my_database
```

```sql
SHOW DATABASES
```

Moving extremely small statements into separate files provides little value.

---

# Future Considerations

Future tooling may include:

- SQL linting.
- SQL formatting checks.
- SQL unit testing.
- Performance benchmarking of metadata queries.

These enhancements naturally build upon the SQL-first architecture.

---

# Guiding Principle

The application should never hide its SQL.

A DBA reading the repository should be able to understand **what the application asks the database** simply by reading the SQL files.

Python exists to orchestrate the workflow; SQL performs the database work.
