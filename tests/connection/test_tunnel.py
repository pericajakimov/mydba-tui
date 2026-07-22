"""Tests for SSH tunnel creation logic."""

from mydba_tui.connection.tunnel import SshTunnel, create_tunnel
from mydba_tui.models.profile import Profile, SshTunnelConfig


def test_create_tunnel_returns_none_without_config() -> None:
    """No tunnel should be created when SSH config is absent."""
    profile = Profile(name="local", host="127.0.0.1")
    assert create_tunnel(profile) is None


def test_create_tunnel_returns_none_with_empty_host() -> None:
    """No tunnel should be created when SSH host is empty."""
    profile = Profile(
        name="empty_ssh",
        host="db.internal",
        ssh_tunnel=SshTunnelConfig(host="", username="user"),
    )
    assert create_tunnel(profile) is None


def test_create_tunnel_returns_tunnel_with_config() -> None:
    """Tunnel should be created when SSH config has a host."""
    profile = Profile(
        name="tunneled",
        host="db.internal",
        port=3306,
        ssh_tunnel=SshTunnelConfig(
            host="jump.example.com",
            port=22,
            username="dba",
            password="secret",
        ),
    )
    tunnel = create_tunnel(profile)
    assert tunnel is not None
    assert isinstance(tunnel, SshTunnel)


def test_tunnel_uses_correct_remote_address() -> None:
    """Tunnel should forward to the profile's host and port."""
    profile = Profile(
        name="test",
        host="internal-db.cluster.local",
        port=3307,
        ssh_tunnel=SshTunnelConfig(host="bastion.example.com", username="admin"),
    )
    tunnel = create_tunnel(profile)
    assert tunnel is not None
    assert tunnel._remote_host == "internal-db.cluster.local"
    assert tunnel._remote_port == 3307
