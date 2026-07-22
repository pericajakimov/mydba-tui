"""Tests for the SQL file loader."""

import pytest

from mydba_tui.services.sql_loader import load_sql


def test_load_schemas_sql() -> None:
    """Should load the schemas SQL file."""
    sql = load_sql("browser/schemas.sql")
    assert "schema_name" in sql
    assert "schemata" in sql


def test_load_nonexistent_file() -> None:
    """Should raise FileNotFoundError for missing SQL files."""
    with pytest.raises(FileNotFoundError):
        load_sql("nonexistent/query.sql")


def test_load_returns_stripped_content() -> None:
    """Loaded SQL should be stripped of leading/trailing whitespace."""
    sql = load_sql("browser/schemas.sql")
    assert not sql.startswith("\n")
    assert not sql.endswith("\n")
