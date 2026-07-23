"""Tests for the SQL file loader."""

import pytest

from mydba_tui.services.sql_loader import load_sql


def test_load_schemas_sql() -> None:
    """Should load the schemas SQL file."""
    sql = load_sql("browser/schema_names.sql")
    assert "schema_name" in sql
    assert "schemata" in sql


def test_load_object_counts_sql() -> None:
    """Should load the object_counts SQL file."""
    sql = load_sql("browser/object_counts.sql")
    assert "tables_count" in sql
    assert "views_count" in sql
    assert "{schema}" in sql


def test_load_tables_sql() -> None:
    """Should load the table names listing SQL file."""
    sql = load_sql("browser/table_names.sql")
    assert "table_name" in sql
    assert "BASE TABLE" in sql
    assert "{schema}" in sql


def test_load_views_sql() -> None:
    """Should load the view names listing SQL file."""
    sql = load_sql("browser/view_names.sql")
    assert "table_name" in sql
    assert "VIEW" in sql


def test_load_procedures_sql() -> None:
    """Should load the procedure names listing SQL file."""
    sql = load_sql("browser/procedure_names.sql")
    assert "routine_name" in sql
    assert "PROCEDURE" in sql


def test_load_triggers_sql() -> None:
    """Should load the trigger names listing SQL file."""
    sql = load_sql("browser/trigger_names.sql")
    assert "trigger_name" in sql


def test_load_table_info_sql() -> None:
    """Should load the table_info SQL file."""
    sql = load_sql("browser/table_info.sql")
    assert "engine" in sql
    assert "{schema}" in sql
    assert "{table}" in sql


def test_load_table_columns_sql() -> None:
    """Should load the table_columns SQL file."""
    sql = load_sql("browser/table_columns.sql")
    assert "column_name" in sql
    assert "column_type" in sql


def test_load_table_indexes_sql() -> None:
    """Should load the table_indexes SQL file."""
    sql = load_sql("browser/table_indexes.sql")
    assert "index_name" in sql
    assert "column_name" in sql


def test_load_index_sizes_sql() -> None:
    """Should load the index_sizes SQL file."""
    sql = load_sql("browser/index_sizes.sql")
    assert "index_name" in sql
    assert "innodb_index_stats" in sql
    assert "{schema}" in sql
    assert "{table}" in sql


def test_load_fk_outgoing_sql() -> None:
    """Should load the table_fk_outgoing SQL file."""
    sql = load_sql("browser/table_fk_outgoing.sql")
    assert "constraint_name" in sql
    assert "referential_constraints" in sql
    assert "{schema}" in sql
    assert "{table}" in sql


def test_load_fk_incoming_sql() -> None:
    """Should load the table_fk_incoming SQL file."""
    sql = load_sql("browser/table_fk_incoming.sql")
    assert "constraint_name" in sql
    assert "referenced_table_name" in sql
    assert "{schema}" in sql
    assert "{table}" in sql


def test_load_table_triggers_sql() -> None:
    """Should load the table_triggers SQL file."""
    sql = load_sql("browser/table_triggers.sql")
    assert "trigger_name" in sql
    assert "action_statement" in sql
    assert "{schema}" in sql
    assert "{table}" in sql


def test_load_nonexistent_file() -> None:
    """Should raise FileNotFoundError for missing SQL files."""
    with pytest.raises(FileNotFoundError):
        load_sql("nonexistent/query.sql")


def test_load_returns_stripped_content() -> None:
    """Loaded SQL should be stripped of leading/trailing whitespace."""
    sql = load_sql("browser/schema_names.sql")
    assert not sql.startswith("\n")
    assert not sql.endswith("\n")
