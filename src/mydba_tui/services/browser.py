"""
Object browser service.

Provides database metadata queries for the object browser.
All SQL is loaded from sql/browser/ files and logged to the SQL log.
"""

import time

from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from mydba_tui.logging import log_sql
from mydba_tui.services.sql_loader import load_sql


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
