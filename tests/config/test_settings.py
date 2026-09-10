"""Tests for application settings management."""

from pathlib import Path

from mydba_tui.config.settings import Settings, load_settings, save_settings


def test_settings_defaults() -> None:
    """Settings should have sensible defaults."""
    settings = Settings()

    assert settings.theme == "textual-dark"
    assert settings.log_level == "WARNING"
    assert settings.sql_log_enabled is True
    assert settings.refresh_interval == 5
    assert settings.export_format == "csv"
    assert settings.result_format == "mysql"


def test_load_settings_creates_file_on_first_run(tmp_path: Path) -> None:
    """First call to load_settings should create settings.yaml with defaults."""
    settings_path = tmp_path / "settings.yaml"

    settings = load_settings(settings_path)

    assert settings_path.exists()
    assert settings.theme == "textual-dark"
    assert settings.log_level == "WARNING"


def test_load_settings_reads_existing_file(tmp_path: Path) -> None:
    """load_settings should read values from an existing settings file."""
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "theme: nord\n"
        "log_level: DEBUG\n"
        "sql_log_enabled: false\n"
        "refresh_interval: 5\n"
        "export_format: tsv\n"
        "result_format: simple\n",
        encoding="utf-8",
    )

    settings = load_settings(settings_path)

    assert settings.theme == "nord"
    assert settings.log_level == "DEBUG"
    assert settings.sql_log_enabled is False
    assert settings.refresh_interval == 5
    assert settings.export_format == "tsv"
    assert settings.result_format == "simple"


def test_load_settings_uses_defaults_for_missing_keys(tmp_path: Path) -> None:
    """Missing keys in settings.yaml should fall back to defaults."""
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text("theme: custom\n", encoding="utf-8")

    settings = load_settings(settings_path)

    assert settings.theme == "custom"
    assert settings.log_level == "WARNING"
    assert settings.result_format == "mysql"


def test_load_settings_handles_empty_file(tmp_path: Path) -> None:
    """An empty settings file should produce default settings."""
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text("", encoding="utf-8")

    settings = load_settings(settings_path)

    assert settings.theme == "textual-dark"
    assert settings.log_level == "WARNING"


def test_save_settings_writes_yaml(tmp_path: Path) -> None:
    """save_settings should write a valid YAML file."""
    settings_path = tmp_path / "settings.yaml"
    settings = Settings(theme="monokai", result_format="simple")

    save_settings(settings, settings_path)

    content = settings_path.read_text(encoding="utf-8")
    assert "theme: monokai" in content
    assert "result_format: simple" in content


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    """Settings should survive a save/load cycle unchanged."""
    settings_path = tmp_path / "settings.yaml"
    original = Settings(
        theme="dark",
        log_level="DEBUG",
        sql_log_enabled=False,
        refresh_interval=10,
        export_format="jsonl",
        result_format="simple",
    )

    save_settings(original, settings_path)
    loaded = load_settings(settings_path)

    assert loaded.theme == original.theme
    assert loaded.log_level == original.log_level
    assert loaded.sql_log_enabled == original.sql_log_enabled
    assert loaded.refresh_interval == original.refresh_interval
    assert loaded.export_format == original.export_format
    assert loaded.result_format == original.result_format
