"""
Connection profile storage.

Handles loading and saving connection profiles from profiles.yaml.
The profiles file is created empty on first run.
"""

from pathlib import Path

import yaml

from mydba_tui.config.paths import ensure_config_dir, get_profiles_path
from mydba_tui.models.profile import Profile


def load_profiles(path: Path | None = None) -> list[Profile]:
    """Load connection profiles from disk.

    If the profiles file does not exist, an empty profiles file is
    created automatically.

    Args:
        path: Optional override for the profiles file path.

    Returns:
        List of Profile instances.
    """
    profiles_path = path or get_profiles_path()

    if not profiles_path.exists():
        save_profiles([], profiles_path)
        return []

    with profiles_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None or "profiles" not in data:
        return []

    raw_profiles: list[dict[str, object]] = data["profiles"]
    return [Profile.from_dict(p) for p in raw_profiles]


def save_profiles(profiles: list[Profile], path: Path | None = None) -> None:
    """Save connection profiles to disk.

    Creates the configuration directory if it does not exist.

    Args:
        profiles: List of Profile instances to save.
        path: Optional override for the profiles file path.
    """
    profiles_path = path or get_profiles_path()
    ensure_config_dir()

    data = {"profiles": [p.to_dict() for p in profiles]}

    with profiles_path.open("w", encoding="utf-8") as f:
        f.write("# mydba connection profiles\n")
        f.write("# See docs/05-connection-manager.md for details.\n\n")
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def add_profile(profile: Profile, path: Path | None = None) -> None:
    """Add a new profile and save to disk.

    Args:
        profile: Profile to add.
        path: Optional override for the profiles file path.

    Raises:
        ValueError: If a profile with the same name already exists.
    """
    profiles = load_profiles(path)

    if any(p.name == profile.name for p in profiles):
        raise ValueError(f"Profile '{profile.name}' already exists")

    profiles.append(profile)
    save_profiles(profiles, path)


def remove_profile(name: str, path: Path | None = None) -> None:
    """Remove a profile by name and save to disk.

    Args:
        name: Name of the profile to remove.
        path: Optional override for the profiles file path.

    Raises:
        ValueError: If the profile is not found.
    """
    profiles = load_profiles(path)
    original_count = len(profiles)
    profiles = [p for p in profiles if p.name != name]

    if len(profiles) == original_count:
        raise ValueError(f"Profile '{name}' not found")

    save_profiles(profiles, path)


def update_profile(profile: Profile, path: Path | None = None) -> None:
    """Update an existing profile by name and save to disk.

    Args:
        profile: Profile with updated values (matched by name).
        path: Optional override for the profiles file path.

    Raises:
        ValueError: If the profile is not found.
    """
    profiles = load_profiles(path)
    found = False

    for i, p in enumerate(profiles):
        if p.name == profile.name:
            profiles[i] = profile
            found = True
            break

    if not found:
        raise ValueError(f"Profile '{profile.name}' not found")

    save_profiles(profiles, path)
