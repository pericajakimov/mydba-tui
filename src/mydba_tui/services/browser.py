"""
Object browser service.

Provides database metadata queries for the object browser.
All SQL is loaded from sql/browser/ files and logged to the SQL log.
"""

import time
from dataclasses import dataclass

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
