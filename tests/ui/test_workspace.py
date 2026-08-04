"""Tests for the SQL Workspace screen."""

from mydba_tui.ui.screens.workspace import WorkspaceScreen


def test_workspace_has_bindings() -> None:
    """Workspace should have execution and navigation bindings."""
    screen = WorkspaceScreen()
    binding_keys = [b.key for b in screen.BINDINGS]

    assert "f5" in binding_keys
    assert "f7" in binding_keys
    assert "f8" in binding_keys
    assert "ctrl+s" in binding_keys
    assert "ctrl+o" in binding_keys
    assert "ctrl+l" in binding_keys
    assert "f6" in binding_keys
    assert "escape" in binding_keys


def test_workspace_split_statements() -> None:
    """_split_statements should split on semicolons."""
    screen = WorkspaceScreen()

    result = screen._split_statements("SELECT 1; SELECT 2; SELECT 3")
    assert result == [("SELECT 1", False), ("SELECT 2", False), ("SELECT 3", False)]


def test_workspace_split_statements_empty() -> None:
    """_split_statements should handle empty input."""
    screen = WorkspaceScreen()

    assert screen._split_statements("") == []
    assert screen._split_statements("   ") == []


def test_workspace_split_statements_single() -> None:
    """_split_statements should handle single statement without semicolon."""
    screen = WorkspaceScreen()

    result = screen._split_statements("SELECT 1")
    assert result == [("SELECT 1", False)]


def test_workspace_split_statements_trailing_semicolon() -> None:
    """_split_statements should ignore trailing semicolon."""
    screen = WorkspaceScreen()

    result = screen._split_statements("SELECT 1;")
    assert result == [("SELECT 1", False)]


def test_workspace_split_statements_multiline() -> None:
    """_split_statements should handle multiline SQL."""
    screen = WorkspaceScreen()

    sql = "SELECT *\nFROM orders\nWHERE id = 1;\n\nSELECT COUNT(*)\nFROM customers;"
    result = screen._split_statements(sql)
    assert len(result) == 2
    assert "FROM orders" in result[0][0]
    assert "FROM customers" in result[1][0]
    assert result[0][1] is False
    assert result[1][1] is False


def test_workspace_split_statements_vertical_output() -> None:
    r"""_split_statements should detect \\G as vertical output terminator."""
    screen = WorkspaceScreen()

    result = screen._split_statements("SELECT * FROM orders\\G")
    assert result == [("SELECT * FROM orders", True)]


def test_workspace_split_statements_mixed_terminators() -> None:
    r"""_split_statements should handle mix of ; and \\G."""
    screen = WorkspaceScreen()

    sql = "SELECT 1; SELECT * FROM orders\\G SELECT 3;"
    result = screen._split_statements(sql)
    assert len(result) == 3
    assert result[0] == ("SELECT 1", False)
    assert result[1] == ("SELECT * FROM orders", True)
    assert result[2] == ("SELECT 3", False)
