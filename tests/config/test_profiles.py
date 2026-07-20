"""Tests for connection profile storage."""

from pathlib import Path

from mydba_tui.config.profiles import load_profiles, save_profiles


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
        "    environment: production\n",
        encoding="utf-8",
    )

    profiles = load_profiles(profiles_path)

    assert len(profiles) == 1
    assert profiles[0]["name"] == "payments"
    assert profiles[0]["host"] == "db.example.com"
    assert profiles[0]["port"] == 3306
    assert profiles[0]["environment"] == "production"


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
        {"name": "local", "host": "127.0.0.1", "port": 3306, "environment": "development"},
    ]

    save_profiles(profiles, profiles_path)

    content = profiles_path.read_text(encoding="utf-8")
    assert "name: local" in content
    assert "host: 127.0.0.1" in content


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    """Profiles should survive a save/load cycle unchanged."""
    profiles_path = tmp_path / "profiles.yaml"
    original = [
        {"name": "prod_writer", "host": "writer.db.internal", "port": 3306},
        {"name": "prod_reader", "host": "reader.db.internal", "port": 3306},
    ]

    save_profiles(original, profiles_path)
    loaded = load_profiles(profiles_path)

    assert len(loaded) == 2
    assert loaded[0]["name"] == "prod_writer"
    assert loaded[1]["name"] == "prod_reader"


def test_save_profiles_multiple_times_overwrites(tmp_path: Path) -> None:
    """Saving profiles should overwrite previous content, not append."""
    profiles_path = tmp_path / "profiles.yaml"

    save_profiles([{"name": "first"}], profiles_path)
    save_profiles([{"name": "second"}], profiles_path)

    loaded = load_profiles(profiles_path)

    assert len(loaded) == 1
    assert loaded[0]["name"] == "second"
