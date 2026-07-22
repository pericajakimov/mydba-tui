"""Tests for server vendor identification logic."""

from mydba_tui.server.detection import ServerInfo, _identify_vendor


def test_identify_oracle_mysql() -> None:
    """Should identify Oracle MySQL from version_comment."""
    info = ServerInfo(version="8.4.0", version_comment="MySQL Community Server - GPL")
    _identify_vendor(info)
    assert info.vendor == "oracle"


def test_identify_percona_server() -> None:
    """Should identify Percona Server from version_comment."""
    info = ServerInfo(version="8.0.35-27", version_comment="Percona Server (GPL)")
    _identify_vendor(info)
    assert info.vendor == "percona"


def test_identify_aurora() -> None:
    """Should identify Aurora when aurora_version is set."""
    info = ServerInfo(
        version="8.0.35",
        version_comment="Source distribution",
        aurora_version="3.04.3",
    )
    _identify_vendor(info)
    assert info.vendor == "aurora"


def test_identify_pxc() -> None:
    """Should identify PXC when wsrep_cluster_name is set."""
    info = ServerInfo(
        version="8.0.35-27",
        version_comment="Percona XtraDB Cluster",
        wsrep_cluster_name="my_cluster",
    )
    _identify_vendor(info)
    assert info.vendor == "pxc"


def test_identify_mariadb() -> None:
    """Should identify MariaDB from version string."""
    info = ServerInfo(version="11.4.2-MariaDB", version_comment="MariaDB Server")
    _identify_vendor(info)
    assert info.vendor == "mariadb"


def test_aurora_takes_priority_over_percona() -> None:
    """Aurora detection should take priority (Aurora uses Percona patches)."""
    info = ServerInfo(
        version="8.0.35",
        version_comment="Source distribution",
        aurora_version="3.04.3",
        wsrep_cluster_name="",
    )
    _identify_vendor(info)
    assert info.vendor == "aurora"


def test_pxc_takes_priority_over_percona_comment() -> None:
    """PXC detection should take priority over generic Percona comment."""
    info = ServerInfo(
        version="8.0.35",
        version_comment="Percona XtraDB Cluster binary",
        wsrep_cluster_name="production_cluster",
    )
    _identify_vendor(info)
    assert info.vendor == "pxc"


def test_unknown_defaults_to_oracle() -> None:
    """Unknown version_comment should default to oracle."""
    info = ServerInfo(version="8.0.35", version_comment="Custom Build")
    _identify_vendor(info)
    assert info.vendor == "oracle"
