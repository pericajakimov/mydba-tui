"""Tests for screen definitions."""

from mydba_tui.ui.screens import (
    AdministrationScreen,
    BrowserScreen,
    HomeScreen,
    MainWorkspaceScreen,
    MonitoringScreen,
    SettingsScreen,
    WorkspaceScreen,
)


def test_home_screen_has_bindings() -> None:
    """Home screen should have connection and exit bindings."""
    screen = HomeScreen()
    binding_keys = [b.key for b in screen.BINDINGS]

    assert "c" in binding_keys
    assert "f10" in binding_keys


def test_main_workspace_has_bindings() -> None:
    """Main workspace should have connection and exit bindings."""
    screen = MainWorkspaceScreen()
    binding_keys = [b.key for b in screen.BINDINGS]

    assert "c" in binding_keys
    assert "w" in binding_keys
    assert "r" in binding_keys
    assert "f10" in binding_keys


def test_module_screens_have_escape_binding() -> None:
    """All module screens should have an Escape binding to go back."""
    screens = [
        BrowserScreen(),
        WorkspaceScreen(),
        AdministrationScreen(),
        MonitoringScreen(),
        SettingsScreen(),
    ]

    for screen in screens:
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys, f"{screen.__class__.__name__} missing escape binding"


def test_all_screens_importable() -> None:
    """All screens should be importable from the screens package."""
    assert HomeScreen is not None
    assert MainWorkspaceScreen is not None
    assert BrowserScreen is not None
    assert WorkspaceScreen is not None
    assert AdministrationScreen is not None
    assert MonitoringScreen is not None
    assert SettingsScreen is not None


def test_app_registers_named_screens() -> None:
    """The app should register all module screens by name."""
    from mydba_tui.app import MyDBAApp

    app = MyDBAApp()
    expected_screens = ["browser", "workspace", "administration", "monitoring", "settings"]

    for name in expected_screens:
        assert name in app.SCREENS, f"Screen '{name}' not registered in app"
