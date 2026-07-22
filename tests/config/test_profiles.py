"""Tests for connection profile storage."""

from pathlib import Path

import pytest

from mydba_tui.config.profiles import (
    add_profile,
    load_profiles,
    remove_profile,
    save_profiles,
    update_profile,
)
from mydba_tui.models.profile import Profile, SslConfig, SshTunnelConfig


def test_load_profiles_creates_file_on_first_run(tmp_path: Path) -> None:
    """First call to load_profiles should create an empty profiles.yaml."""
    profiles_path = tmp_path / "profiles.yaml"

    profiles = load_profiles(profiles_path)

    assert profiles_path.exists()
    assert profiles == []


def test_load_profiles_reads_existing_profiles(tmp_path: Path) -> None:
    """load_profiles should return stored profile data."""
    profiles_path = tmp_path / "profiles.yaml"
    profiles_path.write_text(
        "profiles:\n"
        "  - name: payments\n"
        "    host: db.example.com\n"
        "    port: 3306\n"
        "    environment: prod\n",
        encoding="utf-8",
    )

    profiles = load_profiles(profiles_path)

    assert len(profiles) == 1
    assert profiles[0].name == "payments"
    assert profiles[0].host == "db.example.com"
    assert profiles[0].port == 3306
    assert profiles[0].environment == "prod"


def test_load_profiles_returns_empty_for_no_profiles_key(tmp_path: Path) -> None:
    """A YAML file without a profiles key should return empty list."""
    profiles_path = tmp_path / "profiles.yaml"
    profiles_path.write_text("other_key: value\n", encoding="utf-8")

    profiles = load_profiles(profiles_path)

    assert profiles == []


def test_load_profiles_handles_empty_file(tmp_path: Path) -> None:
    """An empty profiles file should return empty list."""
    profiles_path = tmp_path / "profiles.yaml"
    profiles_path.write_text("", encoding="utf-8")

    profiles = load_profiles(profiles_path)

    assert profiles == []


def test_save_profiles_writes_yaml(tmp_path: Path) -> None:
    """save_profiles should write profiles as valid YAML."""
    profiles_path = tmp_path / "profiles.yaml"
    profiles = [
        Profile(name="local", host="127.0.0.1", port=3306, environment="dev"),
    ]

    save_profiles(profiles, profiles_path)

    content = profiles_path.read_text(encoding="utf-8")
    assert "name: local" in content
    assert "host: 127.0.0.1" in content


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    """Profiles should survive a save/load cycle unchanged."""
    profiles_path = tmp_path / "profiles.yaml"
    original = [
        Profile(name="prod_writer", host="writer.db.internal", port=3306),
        Profile(name="prod_reader", host="reader.db.internal", port=3306),
    ]

    save_profiles(original, profiles_path)
    loaded = load_profiles(profiles_path)

    assert len(loaded) == 2
    assert loaded[0].name == "prod_writer"
    assert loaded[1].name == "prod_reader"


def test_save_profiles_multiple_times_overwrites(tmp_path: Path) -> None:
    """Saving profiles should overwrite previous content, not append."""
    profiles_path = tmp_path / "profiles.yaml"

    save_profiles([Profile(name="first")], profiles_path)
    save_profiles([Profile(name="second")], profiles_path)

    loaded = load_profiles(profiles_path)

    assert len(loaded) == 1
    assert loaded[0].name == "second"


def test_add_profile(tmp_path: Path) -> None:
    """add_profile should append a new profile to the file."""
    profiles_path = tmp_path / "profiles.yaml"
    save_profiles([], profiles_path)

    add_profile(Profile(name="new_server", host="10.0.0.1"), profiles_path)

    loaded = load_profiles(profiles_path)
    assert len(loaded) == 1
    assert loaded[0].name == "new_server"


def test_add_profile_duplicate_raises(tmp_path: Path) -> None:
    """add_profile should raise ValueError for duplicate names."""
    profiles_path = tmp_path / "profiles.yaml"
    save_profiles([Profile(name="existing")], profiles_path)

    with pytest.raises(ValueError, match="already exists"):
        add_profile(Profile(name="existing"), profiles_path)


def test_remove_profile(tmp_path: Path) -> None:
    """remove_profile should delete a profile by name."""
    profiles_path = tmp_path / "profiles.yaml"
    save_profiles(
        [Profile(name="keep"), Profile(name="remove_me")],
        profiles_path,
    )

    remove_profile("remove_me", profiles_path)

    loaded = load_profiles(profiles_path)
    assert len(loaded) == 1
    assert loaded[0].name == "keep"


def test_remove_profile_not_found_raises(tmp_path: Path) -> None:
    """remove_profile should raise ValueError if name not found."""
    profiles_path = tmp_path / "profiles.yaml"
    save_profiles([Profile(name="exists")], profiles_path)

    with pytest.raises(ValueError, match="not found"):
        remove_profile("nonexistent", profiles_path)


def test_update_profile(tmp_path: Path) -> None:
    """update_profile should replace the profile with the same name."""
    profiles_path = tmp_path / "profiles.yaml"
    save_profiles(
        [Profile(name="server", host="old.host.com", port=3306)],
        profiles_path,
    )

    update_profile(Profile(name="server", host="new.host.com", port=3307), profiles_path)

    loaded = load_profiles(profiles_path)
    assert len(loaded) == 1
    assert loaded[0].host == "new.host.com"
    assert loaded[0].port == 3307


def test_update_profile_not_found_raises(tmp_path: Path) -> None:
    """update_profile should raise ValueError if name not found."""
    profiles_path = tmp_path / "profiles.yaml"
    save_profiles([], profiles_path)

    with pytest.raises(ValueError, match="not found"):
        update_profile(Profile(name="ghost"), profiles_path)


def test_profile_with_ssl_roundtrip(tmp_path: Path) -> None:
    """Profiles with SSL config should serialize and deserialize correctly."""
    profiles_path = tmp_path / "profiles.yaml"
    original = Profile(
        name="secure",
        host="ssl.example.com",
        ssl=SslConfig(mode="verify_ca", ca="/path/to/ca.pem"),
    )

    save_profiles([original], profiles_path)
    loaded = load_profiles(profiles_path)

    assert loaded[0].ssl is not None
    assert loaded[0].ssl.ca == "/path/to/ca.pem"
    assert loaded[0].ssl.mode == "verify_ca"


def test_profile_with_ssh_tunnel_roundtrip(tmp_path: Path) -> None:
    """Profiles with SSH tunnel config should serialize and deserialize correctly."""
    profiles_path = tmp_path / "profiles.yaml"
    original = Profile(
        name="tunneled",
        host="internal.db",
        ssh_tunnel=SshTunnelConfig(
            host="jump.example.com", port=22, username="dba", key_file="~/.ssh/id_rsa"
        ),
    )

    save_profiles([original], profiles_path)
    loaded = load_profiles(profiles_path)

    assert loaded[0].ssh_tunnel is not None
    assert loaded[0].ssh_tunnel.host == "jump.example.com"
    assert loaded[0].ssh_tunnel.username == "dba"


def test_profile_to_dict_excludes_empty_optional_fields() -> None:
    """to_dict should not include None ssl/ssh or empty username."""
    profile = Profile(name="minimal", host="db.local")
    data = profile.to_dict()

    assert "ssl" not in data
    assert "ssh_tunnel" not in data
    assert "username" not in data
    assert "password" not in data
