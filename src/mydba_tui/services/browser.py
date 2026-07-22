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
    sql = load_sql("browser/schemas.sql")
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
    "tables": "browser/tables.sql",
    "views": "browser/views.sql",
    "procedures": "browser/procedures.sql",
    "functions": "browser/functions.sql",
    "events": "browser/events.sql",
    "triggers": "browser/triggers.sql",
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
