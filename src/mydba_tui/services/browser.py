"""
Object browser service.

Provides database metadata queries for the object browser.
All SQL is loaded from sql/browser/ files and logged to the SQL log.
"""

import time
from dataclasses import dataclass
from typing import Any

from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from mydba_tui.logging import log_sql
from mydba_tui.services.sql_loader import load_sql


@dataclass(slots=True)
class ObjectCounts:
    """Object counts for a schema.

    Attributes:
        tables: Number of base tables.
        views: Number of views.
        procedures: Number of stored procedures.
        functions: Number of stored functions.
        events: Number of events.
        triggers: Number of triggers.
    """

    tables: int = 0
    views: int = 0
    procedures: int = 0
    functions: int = 0
    events: int = 0
    triggers: int = 0


def get_schemas(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> list[str]:
    """Get the list of schemas (databases) on the server.

    Args:
        connection: Active MySQL connection.

    Returns:
        Sorted list of schema names.
    """
    sql = load_sql("browser/schema_names.sql")
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.schemas")
    return [str(row[0]) for row in rows]  # type: ignore[index]


def get_object_counts(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
) -> ObjectCounts:
    """Get object counts for a schema.

    Args:
        connection: Active MySQL connection.
        schema: Schema name to count objects in.

    Returns:
        ObjectCounts with counts for each object type.
    """
    sql_template = load_sql("browser/object_counts.sql")
    sql = sql_template.replace("{schema}", schema)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    row = cursor.fetchone()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.object_counts")

    if row is None:
        return ObjectCounts()

    return ObjectCounts(
        tables=int(row[0] or 0),  # type: ignore[arg-type,index]
        views=int(row[1] or 0),  # type: ignore[arg-type,index]
        procedures=int(row[2] or 0),  # type: ignore[arg-type,index]
        functions=int(row[3] or 0),  # type: ignore[arg-type,index]
        events=int(row[4] or 0),  # type: ignore[arg-type,index]
        triggers=int(row[5] or 0),  # type: ignore[arg-type,index]
    )


# Mapping of category names to their SQL files
_CATEGORY_SQL_FILES = {
    "tables": "browser/table_names.sql",
    "views": "browser/view_names.sql",
    "procedures": "browser/procedure_names.sql",
    "functions": "browser/function_names.sql",
    "events": "browser/event_names.sql",
    "triggers": "browser/trigger_names.sql",
}


def get_objects(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    category: str,
) -> list[str]:
    """Get the list of objects for a category within a schema.

    Args:
        connection: Active MySQL connection.
        schema: Schema name.
        category: Object category (tables, views, procedures, functions, events, triggers).

    Returns:
        Sorted list of object names.
    """
    sql_file = _CATEGORY_SQL_FILES.get(category)
    if sql_file is None:
        return []

    sql_template = load_sql(sql_file)
    sql = sql_template.replace("{schema}", schema)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, f"browser.{category}")
    return [str(row[0]) for row in rows]  # type: ignore[index]


@dataclass(slots=True)
class TableInfo:
    """General table information.

    Attributes:
        name: Table name.
        engine: Storage engine.
        row_count: Approximate row count.
        avg_row_length: Average row length in bytes.
        data_size: Data size in bytes.
        index_size: Index size in bytes.
        data_free: Free space in bytes.
        auto_increment: Next auto_increment value.
        create_time: Table creation time.
        update_time: Last update time.
        check_time: Last CHECK TABLE time.
        collation: Table collation.
        comment: Table comment.
        row_format: Row format (Dynamic, Compact, etc.).
        create_options: CREATE TABLE options (uppercase).
    """

    name: str = ""
    engine: str = ""
    row_count: int = 0
    avg_row_length: int = 0
    data_size: int = 0
    index_size: int = 0
    data_free: int = 0
    auto_increment: int | None = None
    create_time: str = ""
    update_time: str = ""
    check_time: str = ""
    collation: str = ""
    comment: str = ""
    row_format: str = ""
    create_options: str = ""


@dataclass(slots=True)
class ColumnInfo:
    """Column information.

    Attributes:
        position: Ordinal position.
        name: Column name.
        col_type: Column type (e.g. varchar(255)).
        nullable: Whether the column allows NULL.
        key: Key type (PRI, UNI, MUL, or empty).
        default: Default value.
        extra: Extra info (auto_increment, etc.).
        comment: Column comment.
    """

    position: int = 0
    name: str = ""
    col_type: str = ""
    nullable: str = ""
    key: str = ""
    default: str = ""
    extra: str = ""
    comment: str = ""


@dataclass(slots=True)
class IndexInfo:
    """Index information (one entry per column in index).

    Attributes:
        name: Index name.
        non_unique: Whether the index allows duplicates.
        seq: Sequence number in the index.
        column: Column name or expression.
        cardinality: Estimated number of distinct values.
        nullable: Whether the column can be NULL.
        index_type: Index type (BTREE, HASH, FULLTEXT, SPATIAL).
        visible: Whether the index is visible (YES/NO).
        expression: Functional index expression (MySQL 8.0.13+).
        comment: Index-level comment.
    """

    name: str = ""
    non_unique: int = 0
    seq: int = 0
    column: str = ""
    cardinality: int = 0
    nullable: str = ""
    index_type: str = ""
    visible: str = "YES"
    expression: str = ""
    comment: str = ""


@dataclass(slots=True)
class IndexSizeInfo:
    """Per-index size estimate from InnoDB internal statistics.

    Attributes:
        name: Index name.
        size_bytes: Estimated index size in bytes.
    """

    name: str = ""
    size_bytes: int = 0


@dataclass(slots=True)
class ForeignKeyInfo:
    """Foreign key constraint information (one entry per column in FK).

    Attributes:
        constraint_name: Constraint name.
        column: Source column name.
        referenced_table: Referenced table name.
        referenced_column: Referenced column name.
        ordinal: Position in multi-column FK.
        delete_rule: ON DELETE action (CASCADE, SET NULL, RESTRICT, NO ACTION).
        update_rule: ON UPDATE action.
        source_table: Source table name (populated for incoming FKs only).
    """

    constraint_name: str = ""
    column: str = ""
    referenced_table: str = ""
    referenced_column: str = ""
    ordinal: int = 1
    delete_rule: str = "NO ACTION"
    update_rule: str = "NO ACTION"
    source_table: str = ""


@dataclass(slots=True)
class TriggerInfo:
    """Trigger information for a table.

    Attributes:
        name: Trigger name.
        event: Event type (INSERT, UPDATE, DELETE).
        timing: Action timing (BEFORE, AFTER).
        definer: Definer account (user@host).
        created: Creation timestamp.
        body: Trigger SQL body (action_statement).
    """

    name: str = ""
    event: str = ""
    timing: str = ""
    definer: str = ""
    created: str = ""
    body: str = ""


@dataclass(slots=True)
class PartitionInfo:
    """Partition information for a table.

    Attributes:
        name: Partition name.
        method: Partitioning method (RANGE, LIST, HASH, KEY).
        expression: Partition expression.
        description: Partition description (range value, list values, etc.).
        ordinal: Ordinal position.
        row_count: Approximate row count.
        data_size: Data size in bytes.
        index_size: Index size in bytes.
    """

    name: str = ""
    method: str = ""
    expression: str = ""
    description: str = ""
    ordinal: int = 0
    row_count: int = 0
    data_size: int = 0
    index_size: int = 0


@dataclass(slots=True)
class GrantInfo:
    """Table-level grant information.

    Attributes:
        user: MySQL user name.
        host: Host pattern.
        grant_level: Privilege source (GLOBAL, SCHEMA, TABLE).
        privileges: Comma-separated privilege list.
    """

    user: str = ""
    host: str = ""
    grant_level: str = ""
    privileges: str = ""


def get_table_info(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    table: str,
) -> TableInfo:
    """Get general information about a table.

    Args:
        connection: Active MySQL connection.
        schema: Schema name.
        table: Table name.

    Returns:
        TableInfo with general table metadata.
    """
    sql_template = load_sql("browser/table_info.sql")
    sql = sql_template.replace("{schema}", schema).replace("{table}", table)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    row = cursor.fetchone()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.table_info")

    if row is None:
        return TableInfo(name=table)

    return TableInfo(
        name=str(row[0] or ""),  # type: ignore[index]
        engine=str(row[1] or ""),  # type: ignore[index]
        row_count=int(row[2] or 0),  # type: ignore[arg-type,index]
        avg_row_length=int(row[3] or 0),  # type: ignore[arg-type,index]
        data_size=int(row[4] or 0),  # type: ignore[arg-type,index]
        index_size=int(row[5] or 0),  # type: ignore[arg-type,index]
        data_free=int(row[6] or 0),  # type: ignore[arg-type,index]
        auto_increment=int(row[7]) if row[7] else None,  # type: ignore[arg-type,index]
        create_time=str(row[8] or ""),  # type: ignore[index]
        update_time=str(row[9] or ""),  # type: ignore[index]
        check_time=str(row[10] or ""),  # type: ignore[index]
        collation=str(row[11] or ""),  # type: ignore[index]
        comment=str(row[12] or ""),  # type: ignore[index]
        row_format=str(row[13] or ""),  # type: ignore[index]
        create_options=str(row[14] or "").upper(),  # type: ignore[index]
    )


def get_table_columns(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    table: str,
) -> list[ColumnInfo]:
    """Get column information for a table.

    Args:
        connection: Active MySQL connection.
        schema: Schema name.
        table: Table name.

    Returns:
        List of ColumnInfo for each column.
    """
    sql_template = load_sql("browser/table_columns.sql")
    sql = sql_template.replace("{schema}", schema).replace("{table}", table)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.table_columns")

    return [
        ColumnInfo(
            position=int(row[0] or 0),  # type: ignore[arg-type,index]
            name=str(row[1] or ""),  # type: ignore[index]
            col_type=str(row[2] or ""),  # type: ignore[index]
            nullable=str(row[3] or ""),  # type: ignore[index]
            key=str(row[4] or ""),  # type: ignore[index]
            default=str(row[5]) if row[5] is not None else "NULL",  # type: ignore[index]
            extra=str(row[6] or ""),  # type: ignore[index]
            comment=str(row[7] or ""),  # type: ignore[index]
        )
        for row in rows
    ]


def get_table_indexes(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    table: str,
) -> list[IndexInfo]:
    """Get index information for a table.

    Args:
        connection: Active MySQL connection.
        schema: Schema name.
        table: Table name.

    Returns:
        List of IndexInfo (one per column per index).
    """
    sql_template = load_sql("browser/table_indexes.sql")
    sql = sql_template.replace("{schema}", schema).replace("{table}", table)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.table_indexes")

    return [
        IndexInfo(
            name=str(row[0] or ""),  # type: ignore[index]
            non_unique=int(row[1] or 0),  # type: ignore[arg-type,index]
            seq=int(row[2] or 0),  # type: ignore[arg-type,index]
            column=str(row[3] or ""),  # type: ignore[index]
            cardinality=int(row[4] or 0),  # type: ignore[arg-type,index]
            nullable=str(row[5] or ""),  # type: ignore[index]
            index_type=str(row[6] or ""),  # type: ignore[index]
            visible=str(row[7] or "YES"),  # type: ignore[index]
            expression=str(row[8] or ""),  # type: ignore[index]
            comment=str(row[9] or ""),  # type: ignore[index]
        )
        for row in rows
    ]


def get_index_sizes(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    table: str,
) -> dict[str, int]:
    """Get per-index size estimates from InnoDB internal statistics.

    Queries mysql.innodb_index_stats for the 'size' stat which reports
    index size in pages. Multiplied by @@innodb_page_size to get bytes.

    Returns an empty dict if the user lacks SELECT on mysql.innodb_index_stats
    or the table uses a non-InnoDB engine.

    Args:
        connection: Active MySQL connection.
        schema: Schema name.
        table: Table name.

    Returns:
        Dict mapping index_name → size in bytes.
    """
    sql_template = load_sql("browser/index_sizes.sql")
    sql = sql_template.replace("{schema}", schema).replace("{table}", table)
    start = time.perf_counter()
    try:
        cursor = connection.cursor(buffered=True)
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        duration = time.perf_counter() - start
        log_sql(sql, duration, "browser.index_sizes")
    except Exception:
        # Privilege denied or non-InnoDB table — degrade gracefully
        return {}

    return {
        str(row[0] or ""): int(row[1] or 0)  # type: ignore[arg-type,index]
        for row in rows
    }


def get_table_fk_outgoing(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    table: str,
) -> list[ForeignKeyInfo]:
    """Get outgoing foreign keys defined on this table.

    Args:
        connection: Active MySQL connection.
        schema: Schema name.
        table: Table name.

    Returns:
        List of ForeignKeyInfo (one per column per FK constraint).
    """
    sql_template = load_sql("browser/table_fk_outgoing.sql")
    sql = sql_template.replace("{schema}", schema).replace("{table}", table)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.fk_outgoing")

    return [
        ForeignKeyInfo(
            constraint_name=str(row[0] or ""),  # type: ignore[index]
            column=str(row[1] or ""),  # type: ignore[index]
            referenced_table=str(row[2] or ""),  # type: ignore[index]
            referenced_column=str(row[3] or ""),  # type: ignore[index]
            ordinal=int(row[4] or 1),  # type: ignore[arg-type,index]
            delete_rule=str(row[5] or "NO ACTION"),  # type: ignore[index]
            update_rule=str(row[6] or "NO ACTION"),  # type: ignore[index]
        )
        for row in rows
    ]


def get_table_fk_incoming(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    table: str,
) -> list[ForeignKeyInfo]:
    """Get incoming foreign keys from other tables referencing this table.

    Args:
        connection: Active MySQL connection.
        schema: Schema name.
        table: Table name.

    Returns:
        List of ForeignKeyInfo (one per column per FK constraint).
    """
    sql_template = load_sql("browser/table_fk_incoming.sql")
    sql = sql_template.replace("{schema}", schema).replace("{table}", table)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.fk_incoming")

    return [
        ForeignKeyInfo(
            constraint_name=str(row[0] or ""),  # type: ignore[index]
            source_table=str(row[1] or ""),  # type: ignore[index]
            column=str(row[2] or ""),  # type: ignore[index]
            referenced_column=str(row[3] or ""),  # type: ignore[index]
            ordinal=int(row[4] or 1),  # type: ignore[arg-type,index]
            delete_rule=str(row[5] or "NO ACTION"),  # type: ignore[index]
            update_rule=str(row[6] or "NO ACTION"),  # type: ignore[index]
        )
        for row in rows
    ]


def get_table_triggers(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    table: str,
) -> list[TriggerInfo]:
    """Get triggers defined on a table.

    Args:
        connection: Active MySQL connection.
        schema: Schema name.
        table: Table name.

    Returns:
        List of TriggerInfo for each trigger on the table.
    """
    sql_template = load_sql("browser/table_triggers.sql")
    sql = sql_template.replace("{schema}", schema).replace("{table}", table)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.table_triggers")

    return [
        TriggerInfo(
            name=str(row[0] or ""),  # type: ignore[index]
            event=str(row[1] or ""),  # type: ignore[index]
            timing=str(row[2] or ""),  # type: ignore[index]
            definer=str(row[3] or ""),  # type: ignore[index]
            created=str(row[4] or ""),  # type: ignore[index]
            body=str(row[5] or ""),  # type: ignore[index]
        )
        for row in rows
    ]


def get_table_partitions(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    table: str,
) -> list[PartitionInfo]:
    """Get partition information for a table.

    Returns an empty list for non-partitioned tables.

    Args:
        connection: Active MySQL connection.
        schema: Schema name.
        table: Table name.

    Returns:
        List of PartitionInfo for each partition.
    """
    sql_template = load_sql("browser/table_partitions.sql")
    sql = sql_template.replace("{schema}", schema).replace("{table}", table)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.table_partitions")

    return [
        PartitionInfo(
            name=str(row[0] or ""),  # type: ignore[index]
            method=str(row[1] or ""),  # type: ignore[index]
            expression=str(row[2] or ""),  # type: ignore[index]
            description=str(row[3] or ""),  # type: ignore[index]
            ordinal=int(row[4] or 0),  # type: ignore[arg-type,index]
            row_count=int(row[5] or 0),  # type: ignore[arg-type,index]
            data_size=int(row[6] or 0),  # type: ignore[arg-type,index]
            index_size=int(row[7] or 0),  # type: ignore[arg-type,index]
        )
        for row in rows
    ]


def get_table_grants(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    table: str,
) -> list[GrantInfo]:
    """Get effective privileges on a table from global, schema, and table levels.

    Combines mysql.user (global), mysql.db (schema), and mysql.tables_priv
    (table) to show all users who can access this table and how.

    Returns an empty list if the user lacks SELECT on the mysql grant tables
    or no grants exist for the table.

    Args:
        connection: Active MySQL connection.
        schema: Schema name.
        table: Table name.

    Returns:
        List of GrantInfo for each user/host/level with privileges on the table.
    """
    sql_template = load_sql("browser/table_grants.sql")
    sql = sql_template.replace("{schema}", schema).replace("{table}", table)
    start = time.perf_counter()
    try:
        cursor = connection.cursor(buffered=True)
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        duration = time.perf_counter() - start
        log_sql(sql, duration, "browser.table_grants")
    except Exception:
        # Privilege denied — degrade gracefully
        return []

    return [
        GrantInfo(
            user=str(row[0] or ""),  # type: ignore[index]
            host=str(row[1] or ""),  # type: ignore[index]
            grant_level=str(row[2] or ""),  # type: ignore[index]
            privileges=str(row[3] or ""),  # type: ignore[index]
        )
        for row in rows
    ]


def get_sample_data(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    table: str,
    columns: list[ColumnInfo],
    order: str = "ASC",
    limit: int = 5,
) -> tuple[list[str], list[list[str]]]:
    """Get sample rows from a table and format values client-side.

    Executes a simple SELECT * with ORDER BY primary key. Formatting
    is applied in Python after fetching:
    - Binary > 16 bytes: displayed as '<binary>'
    - Binary <= 16 bytes: displayed as hex (0x...)
    - Text longer than 100 chars: truncated with '...' suffix
    - NULL: displayed as 'NULL'
    - Other values: converted to string as-is

    Args:
        connection: Active MySQL connection.
        schema: Schema name.
        table: Table name.
        columns: Column metadata from get_table_columns().
        order: Sort direction ("ASC" for first rows, "DESC" for last rows).
        limit: Maximum number of rows to return.

    Returns:
        Tuple of (column_names, formatted_rows) where each row is a list of strings.
    """
    # Extract PK columns from cached column metadata
    pk_cols = [col.name for col in columns if col.key == "PRI"]
    col_names = [col.name for col in columns]

    # Build simple query
    order_clause = ""
    if pk_cols:
        pk_str = ", ".join(f"`{c}` {order}" for c in pk_cols)
        order_clause = f" ORDER BY {pk_str}"

    sample_sql = f"SELECT * FROM `{schema}`.`{table}`{order_clause} LIMIT {limit}"
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sample_sql)
    rows = cursor.fetchall()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sample_sql, duration, "browser.sample_data")

    # Format values client-side
    formatted: list[list[str]] = []
    for row in rows:
        formatted_row: list[str] = []
        for i, val in enumerate(row):
            if val is None:
                formatted_row.append("NULL")
            elif i < len(columns):
                formatted_row.append(_format_value(val, columns[i].col_type))
            else:
                formatted_row.append(str(val))
        formatted.append(formatted_row)

    return col_names, formatted


def _format_value(val: Any, col_type: str) -> str:
    """Format a single cell value based on column type."""
    ctype = col_type.lower()

    if _is_binary_type(ctype):
        if isinstance(val, (bytes, bytearray)):
            if len(val) > 16:
                return "<binary>"
            return "0x" + val.hex().upper()
        return str(val)

    if _is_text_type(ctype):
        s = str(val)
        if len(s) > 100:
            return s[:100] + "..."
        return s

    return str(val)


def _is_binary_type(col_type: str) -> bool:
    """Check if a column type is binary/blob."""
    return any(
        t in col_type for t in ("binary", "varbinary", "blob", "tinyblob", "mediumblob", "longblob")
    )


def _is_text_type(col_type: str) -> bool:
    """Check if a column type is text-like and may need truncation."""
    return any(
        t in col_type
        for t in (
            "text",
            "tinytext",
            "mediumtext",
            "longtext",
            "varchar",
            "char",
            "json",
            "enum",
            "set",
        )
    )


# --- View metadata ---


@dataclass(slots=True)
class ViewInfo:
    """General view information.

    Attributes:
        schema: Schema name.
        name: View name.
        definition: View SQL definition.
        check_option: Check option (NONE, LOCAL, CASCADED).
        is_updatable: Whether the view is updatable (YES/NO).
        definer: Definer account.
        security_type: Security type (DEFINER/INVOKER).
        charset: Character set client.
        collation: Collation connection.
    """

    schema: str = ""
    name: str = ""
    definition: str = ""
    check_option: str = "NONE"
    is_updatable: str = ""
    definer: str = ""
    security_type: str = ""
    charset: str = ""
    collation: str = ""


def get_view_info(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    view: str,
) -> ViewInfo:
    """Get general information about a view."""
    sql_template = load_sql("browser/view_info.sql")
    sql = sql_template.replace("{schema}", schema).replace("{view}", view)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    row = cursor.fetchone()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.view_info")

    if row is None:
        return ViewInfo(schema=schema, name=view)

    return ViewInfo(
        schema=str(row[0] or ""),  # type: ignore[index]
        name=str(row[1] or ""),  # type: ignore[index]
        definition=str(row[2] or ""),  # type: ignore[index]
        check_option=str(row[3] or "NONE"),  # type: ignore[index]
        is_updatable=str(row[4] or ""),  # type: ignore[index]
        definer=str(row[5] or ""),  # type: ignore[index]
        security_type=str(row[6] or ""),  # type: ignore[index]
        charset=str(row[7] or ""),  # type: ignore[index]
        collation=str(row[8] or ""),  # type: ignore[index]
    )


# --- Routine (Procedure/Function) metadata ---


@dataclass(slots=True)
class RoutineInfo:
    """General routine (procedure/function) information.

    Attributes:
        schema: Schema name.
        name: Routine name.
        routine_type: PROCEDURE or FUNCTION.
        return_type: Return data type (functions only).
        definition: Routine body.
        is_deterministic: YES/NO.
        data_access: SQL data access (CONTAINS SQL, READS SQL DATA, etc.).
        security_type: DEFINER/INVOKER.
        definer: Definer account.
        created: Creation timestamp.
        last_altered: Last modification timestamp.
        comment: Routine comment.
    """

    schema: str = ""
    name: str = ""
    routine_type: str = ""
    return_type: str = ""
    definition: str = ""
    is_deterministic: str = ""
    data_access: str = ""
    security_type: str = ""
    definer: str = ""
    created: str = ""
    last_altered: str = ""
    comment: str = ""


@dataclass(slots=True)
class RoutineParam:
    """Parameter of a stored procedure or function.

    Attributes:
        ordinal: Ordinal position.
        mode: Parameter mode (IN, OUT, INOUT, or empty for function return).
        name: Parameter name.
        data_type: Data type.
    """

    ordinal: int = 0
    mode: str = ""
    name: str = ""
    data_type: str = ""


def get_routine_info(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    name: str,
    routine_type: str = "PROCEDURE",
) -> RoutineInfo:
    """Get general information about a stored procedure or function."""
    sql_template = load_sql("browser/routine_info.sql")
    sql = (
        sql_template.replace("{schema}", schema)
        .replace("{name}", name)
        .replace("{routine_type}", routine_type)
    )
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    row = cursor.fetchone()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.routine_info")

    if row is None:
        return RoutineInfo(schema=schema, name=name, routine_type=routine_type)

    return RoutineInfo(
        schema=str(row[0] or ""),  # type: ignore[index]
        name=str(row[1] or ""),  # type: ignore[index]
        routine_type=str(row[2] or ""),  # type: ignore[index]
        return_type=str(row[3] or ""),  # type: ignore[index]
        definition=str(row[4] or ""),  # type: ignore[index]
        is_deterministic=str(row[5] or ""),  # type: ignore[index]
        data_access=str(row[6] or ""),  # type: ignore[index]
        security_type=str(row[7] or ""),  # type: ignore[index]
        definer=str(row[8] or ""),  # type: ignore[index]
        created=str(row[9] or ""),  # type: ignore[index]
        last_altered=str(row[10] or ""),  # type: ignore[index]
        comment=str(row[11] or ""),  # type: ignore[index]
    )


def get_routine_params(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    name: str,
    routine_type: str = "PROCEDURE",
) -> list[RoutineParam]:
    """Get parameters for a stored procedure or function."""
    sql_template = load_sql("browser/routine_params.sql")
    sql = (
        sql_template.replace("{schema}", schema)
        .replace("{name}", name)
        .replace("{routine_type}", routine_type)
    )
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.routine_params")

    return [
        RoutineParam(
            ordinal=int(row[0] or 0),  # type: ignore[arg-type,index]
            mode=str(row[1] or ""),  # type: ignore[index]
            name=str(row[2] or ""),  # type: ignore[index]
            data_type=str(row[3] or ""),  # type: ignore[index]
        )
        for row in rows
    ]


# --- Trigger metadata (single trigger detail) ---


@dataclass(slots=True)
class TriggerDetailInfo:
    """Detailed trigger information.

    Attributes:
        schema: Schema name.
        name: Trigger name.
        event: Event (INSERT, UPDATE, DELETE).
        table_schema: Target table schema.
        table_name: Target table name.
        timing: Timing (BEFORE, AFTER).
        body: Trigger body (action_statement).
        action_order: Action order.
        definer: Definer account.
        created: Creation timestamp.
    """

    schema: str = ""
    name: str = ""
    event: str = ""
    table_schema: str = ""
    table_name: str = ""
    timing: str = ""
    body: str = ""
    action_order: int = 0
    definer: str = ""
    created: str = ""


def get_trigger_detail(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    name: str,
) -> TriggerDetailInfo:
    """Get detailed information about a single trigger."""
    sql_template = load_sql("browser/trigger_info.sql")
    sql = sql_template.replace("{schema}", schema).replace("{name}", name)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    row = cursor.fetchone()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.trigger_detail")

    if row is None:
        return TriggerDetailInfo(schema=schema, name=name)

    return TriggerDetailInfo(
        schema=str(row[0] or ""),  # type: ignore[index]
        name=str(row[1] or ""),  # type: ignore[index]
        event=str(row[2] or ""),  # type: ignore[index]
        table_schema=str(row[3] or ""),  # type: ignore[index]
        table_name=str(row[4] or ""),  # type: ignore[index]
        timing=str(row[5] or ""),  # type: ignore[index]
        body=str(row[6] or ""),  # type: ignore[index]
        action_order=int(row[7] or 0),  # type: ignore[arg-type,index]
        definer=str(row[8] or ""),  # type: ignore[index]
        created=str(row[9] or ""),  # type: ignore[index]
    )


# --- Event metadata ---


@dataclass(slots=True)
class EventInfo:
    """Scheduled event information.

    Attributes:
        schema: Schema name.
        name: Event name.
        definer: Definer account.
        event_type: ONE TIME or RECURRING.
        execute_at: Execution time (one-time events).
        interval_value: Interval value (recurring events).
        interval_field: Interval unit (recurring events).
        starts: Start time (recurring events).
        ends: End time (recurring events).
        status: ENABLED, DISABLED, or SLAVESIDE_DISABLED.
        on_completion: PRESERVE or NOT PRESERVE.
        created: Creation timestamp.
        last_altered: Last modification timestamp.
        definition: Event body.
        comment: Event comment.
    """

    schema: str = ""
    name: str = ""
    definer: str = ""
    event_type: str = ""
    execute_at: str = ""
    interval_value: str = ""
    interval_field: str = ""
    starts: str = ""
    ends: str = ""
    status: str = ""
    on_completion: str = ""
    created: str = ""
    last_altered: str = ""
    definition: str = ""
    comment: str = ""


def get_event_info(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    schema: str,
    name: str,
) -> EventInfo:
    """Get information about a scheduled event."""
    sql_template = load_sql("browser/event_info.sql")
    sql = sql_template.replace("{schema}", schema).replace("{name}", name)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    cursor.execute(sql)
    row = cursor.fetchone()
    cursor.close()
    duration = time.perf_counter() - start
    log_sql(sql, duration, "browser.event_info")

    if row is None:
        return EventInfo(schema=schema, name=name)

    return EventInfo(
        schema=str(row[0] or ""),  # type: ignore[index]
        name=str(row[1] or ""),  # type: ignore[index]
        definer=str(row[2] or ""),  # type: ignore[index]
        event_type=str(row[3] or ""),  # type: ignore[index]
        execute_at=str(row[4] or ""),  # type: ignore[index]
        interval_value=str(row[5] or ""),  # type: ignore[index]
        interval_field=str(row[6] or ""),  # type: ignore[index]
        starts=str(row[7] or ""),  # type: ignore[index]
        ends=str(row[8] or ""),  # type: ignore[index]
        status=str(row[9] or ""),  # type: ignore[index]
        on_completion=str(row[10] or ""),  # type: ignore[index]
        created=str(row[11] or ""),  # type: ignore[index]
        last_altered=str(row[12] or ""),  # type: ignore[index]
        definition=str(row[13] or ""),  # type: ignore[index]
        comment=str(row[14] or ""),  # type: ignore[index]
    )
