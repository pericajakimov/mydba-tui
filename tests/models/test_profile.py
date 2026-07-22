"""Tests for the Profile data model."""

from mydba_tui.models.profile import Environment, Profile, SshTunnelConfig, SslConfig, SslMode


def test_profile_defaults() -> None:
    """Profile should have sensible defaults."""
    profile = Profile()

    assert profile.name == ""
    assert profile.environment == "dev"
    assert profile.host == "127.0.0.1"
    assert profile.port == 3306
    assert profile.username == ""
    assert profile.default_database == ""
    assert profile.ssl is None
    assert profile.ssh_tunnel is None
    assert profile.store_password is False
    assert profile.password == ""


def test_profile_from_dict_minimal() -> None:
    """from_dict should create a profile from minimal data."""
    data: dict[str, object] = {"name": "test", "host": "db.local"}
    profile = Profile.from_dict(data)

    assert profile.name == "test"
    assert profile.host == "db.local"
    assert profile.port == 3306
    assert profile.environment == "dev"


def test_profile_from_dict_full() -> None:
    """from_dict should handle all fields."""
    data: dict[str, object] = {
        "name": "production_writer",
        "environment": "prod",
        "host": "writer.aurora.internal",
        "port": 3306,
        "username": "admin",
        "default_database": "payments",
        "connect_timeout": 5,
        "compress": True,
        "init_command": "SET SESSION wait_timeout=3600",
        "ssl": {"mode": "verify_ca", "ca": "/etc/ssl/ca.pem", "cert": "", "key": ""},
        "ssh_tunnel": {
            "host": "jump.internal",
            "port": 22,
            "username": "dba",
            "key_file": "~/.ssh/id_rsa",
        },
        "store_password": False,
    }
    profile = Profile.from_dict(data)

    assert profile.name == "production_writer"
    assert profile.environment == "prod"
    assert profile.host == "writer.aurora.internal"
    assert profile.username == "admin"
    assert profile.default_database == "payments"
    assert profile.connect_timeout == 5
    assert profile.compress is True
    assert profile.init_command == "SET SESSION wait_timeout=3600"
    assert profile.ssl is not None
    assert profile.ssl.mode == "verify_ca"
    assert profile.ssl.ca == "/etc/ssl/ca.pem"
    assert profile.ssh_tunnel is not None
    assert profile.ssh_tunnel.host == "jump.internal"
    assert profile.ssh_tunnel.username == "dba"


def test_profile_to_dict_roundtrip() -> None:
    """to_dict and from_dict should produce equivalent profiles."""
    original = Profile(
        name="roundtrip",
        environment="stage",
        host="stage.db.com",
        port=3307,
        username="reader",
        default_database="analytics",
    )

    data = original.to_dict()
    restored = Profile.from_dict(data)

    assert restored.name == original.name
    assert restored.environment == original.environment
    assert restored.host == original.host
    assert restored.port == original.port
    assert restored.username == original.username
    assert restored.default_database == original.default_database


def test_profile_to_dict_with_ssl() -> None:
    """to_dict should include SSL config when present."""
    profile = Profile(
        name="secure",
        ssl=SslConfig(mode="verify_ca", ca="/ca.pem"),
    )
    data = profile.to_dict()

    assert "ssl" in data
    assert data["ssl"] == {"mode": "verify_ca", "ca": "/ca.pem", "cert": "", "key": ""}


def test_profile_to_dict_with_password() -> None:
    """to_dict should include password only when store_password is True."""
    profile_no_store = Profile(name="no_pass", password="secret")
    assert "password" not in profile_no_store.to_dict()

    profile_store = Profile(name="has_pass", store_password=True, password="secret")
    data = profile_store.to_dict()
    assert data["password"] == "secret"
    assert data["store_password"] is True


def test_environment_enum_values() -> None:
    """Environment enum should have the expected values."""
    assert Environment.PROD.value == "prod"
    assert Environment.STAGE.value == "stage"
    assert Environment.QA.value == "qa"
    assert Environment.DEV.value == "dev"


def test_ssl_config_defaults() -> None:
    """SslConfig should have sensible defaults."""
    ssl = SslConfig()

    assert ssl.mode == "preferred"
    assert ssl.ca == ""
    assert ssl.cert == ""
    assert ssl.key == ""


def test_ssl_mode_enum_values() -> None:
    """SslMode enum should have the expected values."""
    assert SslMode.DISABLED.value == "disabled"
    assert SslMode.PREFERRED.value == "preferred"
    assert SslMode.REQUIRED.value == "required"
    assert SslMode.VERIFY_CA.value == "verify_ca"
    assert SslMode.VERIFY_IDENTITY.value == "verify_identity"


def test_ssh_tunnel_config_defaults() -> None:
    """SshTunnelConfig should have sensible defaults."""
    ssh = SshTunnelConfig()

    assert ssh.host == ""
    assert ssh.port == 22
    assert ssh.username == ""
    assert ssh.key_file == ""
    assert ssh.store_password is False
    assert ssh.password == ""


def test_profile_new_connection_options_defaults() -> None:
    """New connection options should have sensible defaults."""
    profile = Profile()

    assert profile.connect_timeout == 10
    assert profile.compress is False
    assert profile.init_command == ""


def test_profile_to_dict_excludes_default_connection_options() -> None:
    """to_dict should not include connection options at their defaults."""
    profile = Profile(name="minimal", host="db.local")
    data = profile.to_dict()

    assert "connect_timeout" not in data
    assert "compress" not in data
    assert "init_command" not in data


def test_profile_to_dict_includes_non_default_connection_options() -> None:
    """to_dict should include connection options when non-default."""
    profile = Profile(
        name="custom",
        host="db.local",
        connect_timeout=30,
        compress=True,
        init_command="SET SESSION wait_timeout=3600",
    )
    data = profile.to_dict()

    assert data["connect_timeout"] == 30
    assert data["compress"] is True
    assert data["init_command"] == "SET SESSION wait_timeout=3600"
