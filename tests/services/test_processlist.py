"""Tests for the process list service."""

from mydba_tui.server import ServerInfo
from mydba_tui.services.processlist import (
    PROCESS_COLUMNS,
    ProcessRow,
    select_processlist_query,
)


def _info(vendor: str, version: str) -> ServerInfo:
    return ServerInfo(vendor=vendor, version=version)


def test_mysql_8_uses_performance_schema() -> None:
    """MySQL 8.0+ should query performance_schema.processlist."""
    sql = select_processlist_query(_info("oracle", "8.4.0"))
    assert "performance_schema.processlist" in sql


def test_percona_8_uses_performance_schema() -> None:
    """Percona 8.0+ should query performance_schema.processlist."""
    sql = select_processlist_query(_info("percona", "8.0.36"))
    assert "performance_schema.processlist" in sql


def test_aurora_v3_uses_performance_schema() -> None:
    """Aurora (reports as 8.0) should query performance_schema."""
    sql = select_processlist_query(_info("aurora", "8.0.32"))
    assert "performance_schema.processlist" in sql


def test_mariadb_uses_information_schema() -> None:
    """MariaDB should query information_schema.PROCESSLIST."""
    sql = select_processlist_query(_info("mariadb", "10.11.6"))
    assert "information_schema.PROCESSLIST" in sql


def test_old_mysql_falls_back_to_show() -> None:
    """MySQL 5.7 should fall back to SHOW FULL PROCESSLIST."""
    sql = select_processlist_query(_info("oracle", "5.7.44"))
    assert sql == "SHOW FULL PROCESSLIST"


def test_unknown_vendor_falls_back_to_show() -> None:
    """An unknown vendor should fall back to SHOW FULL PROCESSLIST."""
    sql = select_processlist_query(_info("", ""))
    assert sql == "SHOW FULL PROCESSLIST"


def test_none_server_info_falls_back_to_show() -> None:
    """No server info should fall back to SHOW FULL PROCESSLIST."""
    assert select_processlist_query(None) == "SHOW FULL PROCESSLIST"


def test_unparseable_version_falls_back_to_show() -> None:
    """A version string that cannot be parsed should not select perf_schema."""
    sql = select_processlist_query(_info("oracle", "unknown"))
    assert sql == "SHOW FULL PROCESSLIST"


def test_process_row_as_cells_matches_columns() -> None:
    """ProcessRow.as_cells should align with PROCESS_COLUMNS order/length."""
    proc = ProcessRow(
        id=42,
        user="dba",
        host="10.0.0.1",
        db="app",
        command="Query",
        time=3,
        state="executing",
        program="mysql",
        info="SELECT 1",
    )
    cells = proc.as_cells()
    assert len(cells) == len(PROCESS_COLUMNS)
    assert cells[0] == 42
    assert cells[1] == "dba"
    assert cells[-1] == "SELECT 1"


def test_strip_port_ipv4() -> None:
    """A trailing :port is removed from an IPv4 host."""
    from mydba_tui.services.processlist import _strip_port

    assert _strip_port("10.0.0.1:53344") == "10.0.0.1"


def test_strip_port_hostname() -> None:
    """A hostname with a port has the port removed."""
    from mydba_tui.services.processlist import _strip_port

    assert _strip_port("app-server:3306") == "app-server"


def test_strip_port_no_port() -> None:
    """A host with no port is returned unchanged."""
    from mydba_tui.services.processlist import _strip_port

    assert _strip_port("localhost") == "localhost"


def test_strip_port_ipv6_preserved() -> None:
    """An IPv6 address (multiple colons, no trailing digits) is preserved."""
    from mydba_tui.services.processlist import _strip_port

    assert _strip_port("::1") == "::1"
    assert _strip_port("fe80::1") == "fe80::1"


def test_strip_port_empty() -> None:
    """An empty host stays empty."""
    from mydba_tui.services.processlist import _strip_port

    assert _strip_port("") == ""


def test_performance_schema_query_joins_program_name() -> None:
    """The perf_schema query sources the program name from connect attrs."""
    sql = select_processlist_query(_info("oracle", "8.4.0"))
    assert "session_connect_attrs" in sql
    assert "program_name" in sql
    assert "AS Program" in sql


def test_information_schema_query_has_null_program() -> None:
    """The MariaDB query keeps a consistent shape with NULL Program."""
    sql = select_processlist_query(_info("mariadb", "10.11.6"))
    assert "NULL AS Program" in sql
