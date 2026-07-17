"""
Configuration directory and file path resolution.

All platforms use ~/.config/mydba/ as the configuration directory.
"""

from pathlib import Path

CONFIG_DIR_NAME = "mydba"
"""Name of the configuration directory."""

CONFIG_PARENT = ".config"
"""Parent directory under the user's home."""


def get_config_dir() -> Path:
    """Return the configuration directory path.

    The configuration directory is always ~/.config/mydba/ regardless
    of the operating system.

    Returns:
        Path to the configuration directory.
    """
    return Path.home() / CONFIG_PARENT / CONFIG_DIR_NAME


def get_settings_path() -> Path:
    """Return the path to the application settings file.

    Returns:
        Path to settings.yaml.
    """
    return get_config_dir() / "settings.yaml"


def get_profiles_path() -> Path:
    """Return the path to the connection profiles file.

    Returns:
        Path to profiles.yaml.
    """
    return get_config_dir() / "profiles.yaml"


def ensure_config_dir() -> Path:
    """Ensure the configuration directory exists.

    Creates the directory and any parent directories if they do not
    already exist.

    Returns:
        Path to the configuration directory.
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir
