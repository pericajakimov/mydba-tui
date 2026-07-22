"""
Server detection.

Identifies the MySQL server variant, version, role, and session
information immediately after connection. Uses only safe queries
that never error on unsupported platforms.
"""

import time
from dataclasses import dataclass

from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from mydba_tui.logging import log_sql


@dataclass(slots=True)
class ServerInfo:
    """Detected server information.

    Attributes:
        vendor: Server vendor identifier (oracle, percona, pxc, aurora, mariadb).
        version: Server version string (e.g. "8.4.0").
        version_comment: Full version comment from the server.
        role: Server role (writer, reader, primary, replica, or empty).
        hostname: Server hostname.
        port: Server port.
        current_user: Authenticated MySQL user.
        current_database: Active database (may be empty).
        connection_id: MySQL connection ID.
        aurora_version: Aurora version (empty if not Aurora).
        aurora_server_id: Aurora instance ID (empty if not Aurora).
        innodb_version: InnoDB version (useful for Aurora v3 engine context).
        wsrep_cluster_name: PXC/Galera cluster name (empty if not PXC).
        wsrep_node_name: PXC node name (empty if not PXC).
    """

    vendor: str = ""
    version: str = ""
    version_comment: str = ""
    role: str = ""
    hostname: str = ""
    port: int = 3306
    current_user: str = ""
    current_database: str = ""
    connection_id: int = 0
    aurora_version: str = ""
    aurora_server_id: str = ""
    innodb_version: str = ""
    wsrep_cluster_name: str = ""
    wsrep_node_name: str = ""


def detect(connection: MySQLConnectionAbstract | PooledMySQLConnection) -> ServerInfo:
    """Detect server capabilities after connecting.

    Runs a series of lightweight, safe queries to identify the server
    variant, version, role, and session info. Never raises — detection
    failures are handled gracefully with empty values.

    Args:
        connection: An established MySQL connection.

    Returns:
        ServerInfo with detected values.
    """
    info = ServerInfo()

    _detect_version(connection, info)
    _detect_aurora(connection, info)
    _detect_pxc(connection, info)
    _detect_role(connection, info)
    _detect_session(connection, info)
    _identify_vendor(info)

    return info


def _query_one(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    sql: str,
    source: str,
) -> tuple[str, ...] | None:
    """Execute a query and return the first row, or None.

    Args:
        connection: MySQL connection.
        sql: SQL statement.
        source: Source identifier for the SQL log.

    Returns:
        First row as a tuple of strings, or None if no results.
    """
    start = time.perf_counter()
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
        row = cursor.fetchone()
        # Consume remaining results to avoid "Unread result" errors
        cursor.fetchall()
    except Exception:
        row = None
    finally:
        duration = time.perf_counter() - start
        log_sql(sql, duration, source)
        cursor.close()
    if row is None:
        return None
    return tuple(str(v) if v is not None else "" for v in row)


def _query_variable(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    variable_name: str,
    source: str,
) -> str:
    """Read a global variable value safely.

    Uses SHOW GLOBAL VARIABLES LIKE which returns empty on unknown
    variables instead of erroring.

    Args:
        connection: MySQL connection.
        variable_name: Variable name to query.
        source: Source identifier for the SQL log.

    Returns:
        Variable value, or empty string if not found.
    """
    sql = f"SHOW GLOBAL VARIABLES LIKE '{variable_name}'"
    row = _query_one(connection, sql, source)
    if row and len(row) >= 2:
        return str(row[1])
    return ""


def _detect_version(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    info: ServerInfo,
) -> None:
    """Detect server version and hostname."""
    sql = "SELECT @@version, @@version_comment, @@hostname, @@port"
    row = _query_one(connection, sql, "server.detection")
    if row:
        info.version = row[0]
        info.version_comment = row[1]
        info.hostname = row[2]
        info.port = int(row[3]) if row[3] else 3306


def _detect_aurora(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    info: ServerInfo,
) -> None:
    """Detect if the server is AWS Aurora and read Aurora-specific info."""
    info.aurora_version = _query_variable(connection, "aurora_version", "server.detection")
    if info.aurora_version:
        info.aurora_server_id = _query_variable(connection, "aurora_server_id", "server.detection")
        info.innodb_version = _query_variable(connection, "innodb_version", "server.detection")


def _detect_pxc(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    info: ServerInfo,
) -> None:
    """Detect if the server is Percona XtraDB Cluster."""
    info.wsrep_cluster_name = _query_variable(connection, "wsrep_cluster_name", "server.detection")
    if info.wsrep_cluster_name:
        info.wsrep_node_name = _query_variable(connection, "wsrep_node_name", "server.detection")


def _detect_role(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    info: ServerInfo,
) -> None:
    """Detect server role (writer/reader or primary/replica)."""
    # Aurora: check innodb_read_only
    if info.aurora_version:
        value = _query_variable(connection, "innodb_read_only", "server.detection")
        if value.upper() == "ON":
            info.role = "reader"
        else:
            info.role = "writer"
        return

    # Traditional replication: check replica status
    sql = "SHOW REPLICA STATUS"
    row = _query_one(connection, sql, "server.detection")
    if row:
        info.role = "replica"
    else:
        # Could be primary or standalone — check if it has replicas
        sql = "SHOW REPLICAS"
        row = _query_one(connection, sql, "server.detection")
        if row:
            info.role = "primary"
        # else: standalone, leave role empty


def _detect_session(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    info: ServerInfo,
) -> None:
    """Detect current session information."""
    sql = "SELECT CURRENT_USER(), DATABASE(), CONNECTION_ID()"
    row = _query_one(connection, sql, "server.detection")
    if row:
        info.current_user = row[0]
        info.current_database = row[1] if row[1] else ""
        info.connection_id = int(row[2]) if row[2] else 0


def _identify_vendor(info: ServerInfo) -> None:
    """Identify the server vendor from version info."""
    comment = info.version_comment.lower()
    version = info.version.lower()

    if info.aurora_version:
        info.vendor = "aurora"
    elif info.wsrep_cluster_name:
        info.vendor = "pxc"
    elif "percona" in comment:
        info.vendor = "percona"
    elif "mariadb" in version or "mariadb" in comment:
        info.vendor = "mariadb"
    else:
        info.vendor = "oracle"
