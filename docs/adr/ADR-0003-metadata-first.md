# ADR-0003: Metadata-First Navigation

- **Status:** Accepted
- **Date:** 2026-07-17

---

# Context

Traditional SQL clients encourage users to begin exploring a database by viewing table data.

Typical workflow:

```
SHOW DATABASES;

USE mydb;

SHOW TABLES;

SELECT * FROM orders LIMIT 10;
```

Professional DBAs, however, spend considerably more time investigating **metadata** than browsing table contents.

Examples include:

- Table definitions
- Indexes
- Partitions
- Storage statistics
- Triggers
- Replication status
- User privileges
- Dependencies
- Fragmentation
- Object definitions

This observation significantly influenced the design of `mydba`.

---

# Decision

`mydba` adopts a **metadata-first** navigation model.

Selecting an object displays its metadata immediately.

Viewing table data is an explicit action initiated by the user.

---

# Rationale

The primary users of `mydba` are professional MySQL DBAs.

In daily work they are more likely to ask:

- What indexes does this table have?
- How large is it?
- How fragmented is it?
- What partitions exist?
- What triggers are defined?
- Which users have access?
- Which objects depend on it?

than:

> Show me the first ten rows.

Metadata provides significantly more value during routine administration than sample data.

---

# Object Browser Behavior

Selecting a table displays information such as:

- General information
- Data size
- Index size
- Total size
- Row count
- Free space
- Fragmentation
- Storage engine
- DDL
- Columns
- Indexes
- Partitions
- Triggers
- Grants
- Dependencies

Sample data is available only through an explicit action.

---

# Sample Data

Sample data is intentionally **not loaded automatically**.

Instead, the user explicitly requests it.

Typical examples include:

- First rows
- Last rows
- Limited result sets

This avoids unnecessary database activity while keeping navigation responsive.

---

# DDL as the Primary Source

Whenever possible, detailed implementation information is expected to come from the DDL rather than duplicated metadata pages.

For example:

- Charset
- Collation
- Comments
- Create options
- Definer
- Security options

These are already visible in the object's DDL and therefore do not require separate summary pages.

The Browser should avoid presenting duplicate information.

---

# Advantages

The metadata-first approach provides:

- Faster object inspection.
- Less unnecessary SQL execution.
- Better overview of database structure.
- Reduced visual clutter.
- More efficient DBA workflow.

---

# Alternatives Considered

## Data-First Navigation

Rejected.

This model is better suited for application developers who primarily work with table contents.

It is less effective for operational database administration.

---

## Automatically Display Both Metadata and Data

Rejected.

Loading both metadata and sample data every time an object is selected introduces unnecessary queries, additional latency, and visual clutter.

Most inspection tasks require metadata only.

---

# Performance

Because metadata pages execute lightweight queries compared to loading table data, the Object Browser remains responsive even on very large databases.

Large tables should never be scanned automatically.

---

# SQL Transparency

Every metadata query executed by the Browser is written to the SQL log.

This allows DBAs to understand exactly how information is collected and optimize or replace queries in future versions if needed.

---

# Consequences

The Object Browser becomes the primary navigation interface.

The SQL Workspace remains available for ad hoc exploration, while the Browser focuses on presenting concise, high-value metadata.

This significantly reduces repetitive execution of common administrative queries.

---

# Future Considerations

Additional metadata pages may be introduced over time, including:

- Performance statistics
- Storage analysis
- Advanced dependency graphs
- Object history
- Vendor-specific metadata

These additions should continue to follow the metadata-first philosophy without automatically retrieving user data.
