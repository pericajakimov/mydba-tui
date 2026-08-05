"""Tests for the MySQL autocomplete engine."""

from mydba_tui.ui.mysql_autocomplete import (
    CompletionKind,
    get_completions,
    get_completions_after_dot,
)


def test_get_completions_keywords_at_start() -> None:
    """At statement start, only statement starters should be suggested."""
    items = get_completions("SE", at_statement_start=True)
    texts = [i.text for i in items]
    assert "SELECT" in texts
    assert "SET" in texts
    # Functions and types should NOT be at statement start
    assert not any(t.endswith("(") for t in texts)


def test_get_completions_keywords_not_at_start() -> None:
    """Not at start, functions and types should also be offered."""
    items = get_completions("CO")
    texts = [i.text for i in items]
    # Should include keywords like COMMIT, COLUMN
    # and functions like CONCAT(, COALESCE(
    assert any(t.startswith("CO") and t.endswith("(") for t in texts)


def test_get_completions_schema_objects() -> None:
    """Should suggest schema objects when provided."""
    schema_objects = {"tables": ["orders", "order_items", "customers"]}
    items = get_completions("or", schema_objects=schema_objects)
    texts = [i.text for i in items]
    assert "orders" in texts
    assert "order_items" in texts
    assert "customers" not in texts  # doesn't match prefix


def test_get_completions_no_objects_at_start() -> None:
    """Schema objects should not be suggested at statement start."""
    schema_objects = {"tables": ["select_log", "sessions"]}
    items = get_completions("SE", schema_objects=schema_objects, at_statement_start=True)
    texts = [i.text for i in items]
    # Statement starters only
    assert "SELECT" in texts
    # Tables should NOT appear at statement start
    assert "select_log" not in texts
    assert "sessions" not in texts


def test_get_completions_after_dot() -> None:
    """After dot, should suggest columns from the named table."""
    table_columns = {"orders": ["id", "customer_id", "status", "total"]}
    items = get_completions_after_dot("orders", table_columns, "")
    texts = [i.text for i in items]
    assert "id" in texts
    assert "status" in texts
    assert len(items) == 4


def test_get_completions_after_dot_with_prefix() -> None:
    """After dot with prefix, should filter columns."""
    table_columns = {"orders": ["id", "customer_id", "status", "total"]}
    items = get_completions_after_dot("orders", table_columns, "st")
    texts = [i.text for i in items]
    assert "status" in texts
    assert "id" not in texts


def test_get_completions_limit() -> None:
    """Should limit results to 50 items."""
    items = get_completions("A")
    assert len(items) <= 50


def test_completion_kinds() -> None:
    """Items should have proper kinds assigned."""
    items = get_completions("SEL", at_statement_start=True)
    select = next(i for i in items if i.text == "SELECT")
    assert select.kind == CompletionKind.KEYWORD

    items = get_completions("CONC")
    concat = next((i for i in items if i.text == "CONCAT("), None)
    if concat:
        assert concat.kind == CompletionKind.FUNCTION
