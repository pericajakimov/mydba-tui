"""Tests for the Reconnect feature's endpoint-comparison logic.

The endpoint decision drives whether a new connection preserves the SQL
workspace session (same host/port/user) or rotates the log and clears the
editor (a genuine profile switch).
"""

from mydba_tui.app import MyDBAApp
from mydba_tui.models.profile import Profile


def _profile(**overrides: object) -> Profile:
    """Build a Profile with sensible defaults, overriding named fields."""
    base = {
        "name": "primary",
        "host": "db1.example.com",
        "port": 3306,
        "username": "dba",
    }
    base.update(overrides)
    return Profile(**base)  # type: ignore[arg-type]


def test_same_endpoint_identical_profiles() -> None:
    """Two profiles with the same host/port/user are the same endpoint."""
    a = _profile()
    b = _profile()
    assert MyDBAApp._same_endpoint(a, b) is True


def test_same_endpoint_ignores_name_and_environment() -> None:
    """Endpoint identity ignores profile name and environment."""
    a = _profile(name="primary", environment="prod")
    b = _profile(name="renamed", environment="dev")
    assert MyDBAApp._same_endpoint(a, b) is True


def test_different_host_is_different_endpoint() -> None:
    """A different host is a different endpoint."""
    a = _profile(host="db1.example.com")
    b = _profile(host="db2.example.com")
    assert MyDBAApp._same_endpoint(a, b) is False


def test_different_port_is_different_endpoint() -> None:
    """A different port is a different endpoint."""
    a = _profile(port=3306)
    b = _profile(port=3307)
    assert MyDBAApp._same_endpoint(a, b) is False


def test_different_username_is_different_endpoint() -> None:
    """A different username is a different endpoint (fresh session context)."""
    a = _profile(username="dba")
    b = _profile(username="readonly")
    assert MyDBAApp._same_endpoint(a, b) is False


def test_none_previous_is_not_same_endpoint() -> None:
    """No previous profile (first connect) is never a same-endpoint reconnect."""
    assert MyDBAApp._same_endpoint(None, _profile()) is False


def test_both_none_is_not_same_endpoint() -> None:
    """Two missing profiles are not considered the same endpoint."""
    assert MyDBAApp._same_endpoint(None, None) is False


def test_workspace_has_reconnect_binding() -> None:
    """SQL workspace exposes reconnect via ctrl+shift+x (editor-safe)."""
    from mydba_tui.ui.screens.workspace import WorkspaceScreen

    keys = [b.key for b in WorkspaceScreen.BINDINGS]
    assert "ctrl+shift+x" in keys


def test_main_workspace_has_reconnect_binding() -> None:
    """Object browser exposes reconnect via the bare 'x' key."""
    from mydba_tui.ui.screens.main_workspace import MainWorkspaceScreen

    keys = [b.key for b in MainWorkspaceScreen.BINDINGS]
    assert "x" in keys
