"""
Connection statistics service.

Aggregates the current process list into per-(user, host) connection counts
for the Administration Connections view. Reuses fetch_processes so the query
source is version-gated and the client host is already port-stripped.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mydba_tui.services.processlist import fetch_processes

if TYPE_CHECKING:
    from mysql.connector.abstracts import MySQLConnectionAbstract
    from mysql.connector.pooling import PooledMySQLConnection

    from mydba_tui.server import ServerInfo


@dataclass(slots=True)
class ConnectionStat:
    """A connection count for a (user, host) group.

    Attributes:
        user: MySQL user.
        host: Client host IP (client source port already stripped).
        count: Number of active connections in this group.
    """

    user: str
    host: str
    count: int


def fetch_connection_stats(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    server_info: ServerInfo | None,
) -> list[ConnectionStat]:
    """Fetch connection counts grouped by (user, host).

    Args:
        connection: Active MySQL connection.
        server_info: Detected server information (drives the process query).

    Returns:
        List of ConnectionStat sorted by count descending, then user, then host.
    """
    processes = fetch_processes(connection, server_info)
    counter: Counter[tuple[str, str]] = Counter((proc.user, proc.host) for proc in processes)
    stats = [
        ConnectionStat(user=user, host=host, count=count) for (user, host), count in counter.items()
    ]
    stats.sort(key=lambda s: (-s.count, s.user.lower(), s.host.lower()))
    return stats
