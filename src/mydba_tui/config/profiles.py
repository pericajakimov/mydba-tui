"""
Connection profile storage.

Handles loading and saving connection profiles from profiles.yaml.
The profiles file is created empty on first run.
"""

from pathlib import Path

import yaml

from mydba_tui.config.paths import ensure_config_dir, get_profiles_path


def load_profiles(path: Path | None = None) -> list[dict[str, object]]:
    """Load connection profiles from disk.

    If the profiles file does not exist, an empty profiles file is
    created automatically.

    Args:
        path: Optional override for the profiles file path.

    Returns:
        List of profile dictionaries.
    """
    profiles_path = path or get_profiles_path()

    if not profiles_path.exists():
        save_profiles([], profiles_path)
        return []

    with profiles_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None or "profiles" not in data:
        return []

    profiles: list[dict[str, object]] = data["profiles"]
    return profiles


def save_profiles(
    profiles: list[dict[str, object]], path: Path | None = None
) -> None:
    """Save connection profiles to disk.

    Creates the configuration directory if it does not exist.

    Args:
        profiles: List of profile dictionaries to save.
        path: Optional override for the profiles file path.
    """
    profiles_path = path or get_profiles_path()
    ensure_config_dir()

    data = {"profiles": profiles}

    with profiles_path.open("w", encoding="utf-8") as f:
        f.write("# mydba connection profiles\n")
        f.write("# See docs/05-connection-manager.md for details.\n\n")
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
