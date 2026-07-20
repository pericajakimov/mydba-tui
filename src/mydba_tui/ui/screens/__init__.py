"""
Screen definitions for mydba-tui.

Each module has its own screen. The home screen provides navigation
to all available modules.
"""

from mydba_tui.ui.screens.administration import AdministrationScreen
from mydba_tui.ui.screens.browser import BrowserScreen
from mydba_tui.ui.screens.home import HomeScreen
from mydba_tui.ui.screens.monitoring import MonitoringScreen
from mydba_tui.ui.screens.settings import SettingsScreen
from mydba_tui.ui.screens.workspace import WorkspaceScreen

__all__ = [
    "AdministrationScreen",
    "BrowserScreen",
    "HomeScreen",
    "MonitoringScreen",
    "SettingsScreen",
    "WorkspaceScreen",
]
