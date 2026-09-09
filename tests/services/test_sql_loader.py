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


def test_load_table_partitions_sql() -> None:
    """Should load the table_partitions SQL file."""
    sql = load_sql("browser/table_partitions.sql")
    assert "partition_name" in sql
    assert "partition_description" in sql
    assert "{schema}" in sql
    assert "{table}" in sql


def test_load_table_grants_sql() -> None:
    """Should load the table_grants SQL file."""
    sql = load_sql("browser/table_grants.sql")
    assert "table_priv" in sql
    assert "tables_priv" in sql
    assert "mysql.user" in sql
    assert "mysql.db" in sql
    assert "columns_priv" in sql
    assert "{schema}" in sql
    assert "{table}" in sql


def test_load_view_info_sql() -> None:
    """Should load the view_info SQL file."""
    sql = load_sql("browser/view_info.sql")
    assert "view_definition" in sql
    assert "is_updatable" in sql
    assert "{schema}" in sql
    assert "{view}" in sql


def test_load_routine_info_sql() -> None:
    """Should load the routine_info SQL file."""
    sql = load_sql("browser/routine_info.sql")
    assert "routine_definition" in sql
    assert "is_deterministic" in sql
    assert "{schema}" in sql
    assert "{name}" in sql
    assert "{routine_type}" in sql


def test_load_routine_params_sql() -> None:
    """Should load the routine_params SQL file."""
    sql = load_sql("browser/routine_params.sql")
    assert "parameter_mode" in sql
    assert "parameter_name" in sql
    assert "{schema}" in sql
    assert "{name}" in sql


def test_load_trigger_info_sql() -> None:
    """Should load the trigger_info SQL file."""
    sql = load_sql("browser/trigger_info.sql")
    assert "trigger_name" in sql
    assert "action_timing" in sql
    assert "event_object_table" in sql
    assert "{schema}" in sql
    assert "{name}" in sql


def test_load_event_info_sql() -> None:
    """Should load the event_info SQL file."""
    sql = load_sql("browser/event_info.sql")
    assert "event_type" in sql
    assert "event_definition" in sql
    assert "{schema}" in sql
    assert "{name}" in sql


def test_load_nonexistent_file() -> None:
    """Should raise FileNotFoundError for missing SQL files."""
    with pytest.raises(FileNotFoundError):
        load_sql("nonexistent/query.sql")


def test_load_returns_stripped_content() -> None:
    """Loaded SQL should be stripped of leading/trailing whitespace."""
    sql = load_sql("browser/schema_names.sql")
    assert not sql.startswith("\n")
    assert not sql.endswith("\n")


# --- Extracted admin / dependency / workspace queries ---

_EXTRACTED_SQL_FILES = [
    "admin/processlist_performance_schema.sql",
    "admin/processlist_information_schema.sql",
    "admin/transactions.sql",
    "admin/statement_history.sql",
    "admin/lock_waits.sql",
    "admin/metadata_lock_waits.sql",
    "admin/users.sql",
    "browser/dep_views.sql",
    "browser/dep_procedures.sql",
    "browser/dep_functions.sql",
    "browser/dep_triggers.sql",
    "browser/dep_events.sql",
    "browser/dep_tables.sql",
    "browser/dep_foreign_keys.sql",
    "workspace/schema_names.sql",
    "workspace/objects_in_current_db.sql",
    "workspace/routines_in_current_db.sql",
    "workspace/objects_in_schema.sql",
]


@pytest.mark.parametrize("relative_path", _EXTRACTED_SQL_FILES)
def test_extracted_sql_files_load(relative_path: str) -> None:
    """Every extracted .sql file exists and returns non-empty SQL."""
    sql = load_sql(relative_path)
    assert sql.strip(), f"{relative_path} is empty"
    assert "SELECT" in sql.upper()


def test_statement_history_has_conn_id_placeholder() -> None:
    """The statement history query exposes the {conn_id} placeholder."""
    sql = load_sql("admin/statement_history.sql")
    assert "{conn_id}" in sql
    assert "events_statements_history" in sql


def test_workspace_queries_have_schema_placeholder() -> None:
    """The schema-scoped autocomplete queries expose the {schema} placeholder."""
    for path in (
        "workspace/objects_in_current_db.sql",
        "workspace/routines_in_current_db.sql",
        "workspace/objects_in_schema.sql",
    ):
        assert "{schema}" in load_sql(path), f"{path} missing placeholder"


def test_missing_sql_file_raises() -> None:
    """Loading a non-existent SQL file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_sql("admin/does_not_exist.sql")


# --- Tagging and header stripping ---

from mydba_tui.services.sql_loader import tag_sql  # noqa: E402


def test_tag_sql_prefixes_marker() -> None:
    """tag_sql prepends the mydba marker."""
    assert tag_sql("SELECT 1") == "/* mydba */ SELECT 1"


def test_loaded_sql_is_tagged() -> None:
    """load_sql output carries the mydba marker for process-list visibility."""
    sql = load_sql("browser/schema_names.sql")
    assert sql.startswith("/* mydba */")


def test_loaded_sql_strips_header_comments() -> None:
    """The file's leading -- comment header is not sent to the server."""
    sql = load_sql("admin/transactions.sql")
    # The human header (e.g. "-- Active InnoDB transactions...") is removed.
    assert "-- Active InnoDB" not in sql
    assert "Called from" not in sql
    # The actual statement survives.
    assert "innodb_trx" in sql


def test_loaded_sql_starts_with_statement_after_tag() -> None:
    """After the tag, the text begins with SQL, not a comment line."""
    sql = load_sql("browser/dep_views.sql")
    body = sql[len("/* mydba */ ") :]
    assert not body.lstrip().startswith("--")
    assert body.upper().startswith("SELECT")


def test_users_sql_contains_all_group_labels() -> None:
    """The users query classifies into all six documented groups."""
    sql = load_sql("admin/users.sql")
    for label in (
        "System Users",
        "Admin Users",
        "Personal Users",
        "Application Users",
        "Replication Users",
        "Monitoring Users",
        "Read-Only Users",
        "Special Purpose Users",
    ):
        assert label in sql, f"missing group label {label}"
    assert "mysql.user" in sql
    assert "mysql.db" in sql
    assert "password_last_changed" in sql
    assert "group_color" in sql
