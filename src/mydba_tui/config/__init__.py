"""
Configuration package.

Handles application settings, user preferences, connection profiles,
and environment-specific configuration loading.

Configuration is stored in ~/.config/mydba/ on all platforms.
"""

from mydba_tui.config.paths import ensure_config_dir, get_config_dir
from mydba_tui.config.profiles import load_profiles, save_profiles
from mydba_tui.config.settings import Settings, load_settings, save_settings

__all__ = [
    "Settings",
    "ensure_config_dir",
    "get_config_dir",
    "load_profiles",
    "load_settings",
    "save_profiles",
    "save_settings",
]
