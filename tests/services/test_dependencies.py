"""Tests for the dependency analysis engine."""

from unittest.mock import MagicMock, patch

from mydba_tui.services.dependencies import (
    DependencyGraph,
    ObjectRef,
    ObjectType,
    _parse_references,
    build_dependency_graph,
)

# --- ObjectRef ---


def test_object_ref_str() -> None:
    """ObjectRef str should return schema.name."""
    ref = ObjectRef(schema="sales", name="orders", obj_type=ObjectType.TABLE)
    assert str(ref) == "sales.orders"


def test_object_ref_frozen() -> None:
    """ObjectRef should be hashable (frozen dataclass)."""
    ref = ObjectRef(schema="sales", name="orders", obj_type=ObjectType.TABLE)
    assert hash(ref)
    s = {ref}
    assert ref in s


# --- DependencyGraph ---


def test_graph_add_object() -> None:
    """Graph should register objects."""
    graph = DependencyGraph()
    obj = ObjectRef(schema="sales", name="orders", obj_type=ObjectType.TABLE)
    graph.add_object(obj)
    assert "TABLE:sales.orders" in graph.objects


def test_graph_add_dependency() -> None:
    """Graph should store forward and reverse edges."""
    graph = DependencyGraph()
    source = ObjectRef(schema="sales", name="active_orders", obj_type=ObjectType.VIEW)
    target = ObjectRef(schema="sales", name="orders", obj_type=ObjectType.TABLE)
    graph.add_object(source)
    graph.add_object(target)
    graph.add_dependency(source, target)

    assert target in graph.get_dependencies(source)
    assert source in graph.get_dependents(target)


def test_graph_get_dependents_by_name() -> None:
    """get_dependents_by_name should find dependents regardless of target type."""
    graph = DependencyGraph()
    table = ObjectRef(schema="sales", name="orders", obj_type=ObjectType.TABLE)
    view = ObjectRef(schema="sales", name="active_orders", obj_type=ObjectType.VIEW)
    proc = ObjectRef(schema="sales", name="archive_orders", obj_type=ObjectType.PROCEDURE)

    graph.add_object(table)
    graph.add_object(view)
    graph.add_object(proc)
    graph.add_dependency(view, table)
    graph.add_dependency(proc, table)

    dependents = graph.get_dependents_by_name("sales", "orders")
    assert len(dependents) == 2
    assert view in dependents
    assert proc in dependents


def test_graph_no_dependents() -> None:
    """get_dependents_by_name should return empty list for unreferenced objects."""
    graph = DependencyGraph()
    table = ObjectRef(schema="sales", name="orphan", obj_type=ObjectType.TABLE)
    graph.add_object(table)

    dependents = graph.get_dependents_by_name("sales", "orphan")
    assert dependents == []


# --- _parse_references ---


def test_parse_references_simple_select() -> None:
    """Should extract table references from a simple SELECT."""
    refs = _parse_references("SELECT * FROM orders", "sales")
    assert "sales.orders" in refs


def test_parse_references_qualified_name() -> None:
    """Should preserve explicit schema qualification."""
    refs = _parse_references("SELECT * FROM archive.orders", "sales")
    assert "archive.orders" in refs
    assert "sales.orders" not in refs


def test_parse_references_join() -> None:
    """Should extract all tables from a JOIN."""
    sql = "SELECT * FROM orders o JOIN customers c ON o.cid = c.id"
    refs = _parse_references(sql, "sales")
    assert "sales.orders" in refs
    assert "sales.customers" in refs


def test_parse_references_subquery() -> None:
    """Should extract tables from subqueries."""
    sql = "SELECT * FROM orders WHERE id IN (SELECT order_id FROM items)"
    refs = _parse_references(sql, "sales")
    assert "sales.orders" in refs
    assert "sales.items" in refs


def test_parse_references_insert_select() -> None:
    """Should extract tables from INSERT ... SELECT."""
    sql = "INSERT INTO archive.orders SELECT * FROM sales.orders WHERE dt < NOW()"
    refs = _parse_references(sql, "sales")
    assert "archive.orders" in refs
    assert "sales.orders" in refs


def test_parse_references_empty_definition() -> None:
    """Should return empty list for empty/null definitions."""
    assert _parse_references("", "sales") == []
    assert _parse_references("   ", "sales") == []


def test_parse_references_invalid_sql() -> None:
    """Should handle invalid SQL gracefully."""
    refs = _parse_references("THIS IS NOT VALID SQL AT ALL !!!", "sales")
    # Should not crash, may return empty or partial results
    assert isinstance(refs, list)


def test_parse_references_cte() -> None:
    """Should extract tables from CTEs."""
    sql = """
    WITH recent AS (SELECT * FROM orders WHERE dt > '2024-01-01')
    SELECT r.*, c.name FROM recent r JOIN customers c ON r.cid = c.id
    """
    refs = _parse_references(sql, "sales")
    assert "sales.orders" in refs
    assert "sales.customers" in refs


def test_parse_references_multiple_schemas() -> None:
    """Should correctly resolve mixed qualified and unqualified names."""
    sql = "SELECT * FROM orders o JOIN reporting.summary s ON o.id = s.order_id"
    refs = _parse_references(sql, "sales")
    assert "sales.orders" in refs
    assert "reporting.summary" in refs


# --- build_dependency_graph ---


@patch("mydba_tui.services.dependencies._enumerate_foreign_keys")
@patch("mydba_tui.services.dependencies._enumerate_objects")
@patch("mydba_tui.services.dependencies._enumerate_tables")
def test_build_dependency_graph(
    mock_tables: MagicMock,
    mock_objects: MagicMock,
    mock_fks: MagicMock,
) -> None:
    """build_dependency_graph should connect objects via parsed SQL references."""
    mock_tables.return_value = [
        ObjectRef(schema="sales", name="orders", obj_type=ObjectType.TABLE),
        ObjectRef(schema="sales", name="customers", obj_type=ObjectType.TABLE),
    ]

    view_ref = ObjectRef(schema="sales", name="active_orders", obj_type=ObjectType.VIEW)
    mock_objects.return_value = [
        (view_ref, "SELECT * FROM orders WHERE status = 'active'"),
    ]

    mock_fks.return_value = []

    mock_conn = MagicMock()
    graph = build_dependency_graph(mock_conn, ["sales"])

    # View should depend on orders table
    deps = graph.get_dependencies(view_ref)
    assert any(d.name == "orders" and d.schema == "sales" for d in deps)

    # Orders table should have the view as a dependent
    dependents = graph.get_dependents_by_name("sales", "orders")
    assert any(d.name == "active_orders" for d in dependents)


@patch("mydba_tui.services.dependencies._enumerate_foreign_keys")
@patch("mydba_tui.services.dependencies._enumerate_objects")
@patch("mydba_tui.services.dependencies._enumerate_tables")
def test_build_dependency_graph_with_fks(
    mock_tables: MagicMock,
    mock_objects: MagicMock,
    mock_fks: MagicMock,
) -> None:
    """build_dependency_graph should include FK-based dependencies."""
    mock_tables.return_value = [
        ObjectRef(schema="sales", name="orders", obj_type=ObjectType.TABLE),
        ObjectRef(schema="sales", name="customers", obj_type=ObjectType.TABLE),
    ]

    mock_objects.return_value = []

    mock_fks.return_value = [
        ("sales", "orders", "sales", "customers"),
    ]

    mock_conn = MagicMock()
    graph = build_dependency_graph(mock_conn, ["sales"])

    # orders should depend on customers via FK
    orders = ObjectRef(schema="sales", name="orders", obj_type=ObjectType.TABLE)
    deps = graph.get_dependencies(orders)
    assert any(d.name == "customers" and d.schema == "sales" for d in deps)


@patch("mydba_tui.services.dependencies._enumerate_foreign_keys")
@patch("mydba_tui.services.dependencies._enumerate_objects")
@patch("mydba_tui.services.dependencies._enumerate_tables")
def test_build_dependency_graph_skip_self_reference(
    mock_tables: MagicMock,
    mock_objects: MagicMock,
    mock_fks: MagicMock,
) -> None:
    """build_dependency_graph should not create self-referencing edges."""
    mock_tables.return_value = [
        ObjectRef(schema="sales", name="orders", obj_type=ObjectType.TABLE),
    ]

    view_ref = ObjectRef(schema="sales", name="v_orders", obj_type=ObjectType.VIEW)
    # View definition references itself (edge case)
    mock_objects.return_value = [
        (view_ref, "SELECT * FROM v_orders WHERE 1=0"),
    ]

    mock_fks.return_value = []

    mock_conn = MagicMock()
    graph = build_dependency_graph(mock_conn, ["sales"])

    deps = graph.get_dependencies(view_ref)
    assert not any(d.name == "v_orders" for d in deps)
