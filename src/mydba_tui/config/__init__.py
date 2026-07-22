"""
Configuration package.

Handles application settings, user preferences, connection profiles,
and environment-specific configuration loading.

Configuration is stored in ~/.config/mydba/ on all platforms.
"""

from mydba_tui.config.paths import ensure_config_dir, get_config_dir
from mydba_tui.config.profiles import (
    add_profile,
    load_profiles,
    remove_profile,
    save_profiles,
    update_profile,
)
from mydba_tui.config.settings import Settings, load_settings, save_settings

__all__ = [
    "Settings",
    "add_profile",
    "ensure_config_dir",
    "get_config_dir",
    "load_profiles",
    "load_settings",
    "remove_profile",
    "save_profiles",
    "save_settings",
    "update_profile",
]
