"""
Dependency Analysis Engine.

Discovers relationships between MySQL database objects by parsing SQL
definitions with sqlglot and building an in-memory dependency graph.

Layers:
    1. Object Enumeration — discover all objects from information_schema
    2. SQL Parser — extract raw object references from definitions
    3. Name Resolver — normalize to fully-qualified schema.name
    4. Dependency Graph — adjacency list with forward and reverse lookups
"""

import time
from dataclasses import dataclass, field
from enum import Enum

import sqlglot
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection
from sqlglot import exp

from mydba_tui.logging import log_sql
from mydba_tui.services.sql_loader import load_sql


class ObjectType(Enum):
    """Database object types tracked by the dependency engine."""

    TABLE = "TABLE"
    VIEW = "VIEW"
    PROCEDURE = "PROCEDURE"
    FUNCTION = "FUNCTION"
    TRIGGER = "TRIGGER"
    EVENT = "EVENT"


@dataclass(slots=True, frozen=True)
class ObjectRef:
    """Fully-qualified reference to a database object.

    Attributes:
        schema: Schema name.
        name: Object name.
        obj_type: Object type.
    """

    schema: str
    name: str
    obj_type: ObjectType

    def __str__(self) -> str:
        return f"{self.schema}.{self.name}"


@dataclass(slots=True)
class Dependency:
    """A directed dependency between two objects.

    Attributes:
        source: The object that contains the reference.
        target: The object being referenced.
    """

    source: ObjectRef
    target: ObjectRef


@dataclass
class DependencyGraph:
    """In-memory dependency graph with forward and reverse lookups.

    Attributes:
        objects: All known database objects.
        forward: source → list of targets (what does this object reference?).
        reverse: target → list of sources (who references this object?).
    """

    objects: dict[str, ObjectRef] = field(default_factory=dict)
    forward: dict[str, list[ObjectRef]] = field(default_factory=dict)
    reverse: dict[str, list[ObjectRef]] = field(default_factory=dict)
    edge_labels: dict[str, str] = field(default_factory=dict)

    def add_object(self, obj: ObjectRef) -> None:
        """Register an object in the graph."""
        key = f"{obj.obj_type.value}:{obj.schema}.{obj.name}"
        self.objects[key] = obj

    def add_dependency(self, source: ObjectRef, target: ObjectRef, label: str = "") -> None:
        """Add a directed dependency edge with an optional label."""
        src_key = f"{source.obj_type.value}:{source.schema}.{source.name}"
        tgt_key = f"{target.obj_type.value}:{target.schema}.{target.name}"

        if src_key not in self.forward:
            self.forward[src_key] = []
        self.forward[src_key].append(target)

        if tgt_key not in self.reverse:
            self.reverse[tgt_key] = []
        self.reverse[tgt_key].append(source)

        if label:
            edge_key = f"{src_key}->{tgt_key}"
            self.edge_labels[edge_key] = label

    def get_dependencies(self, obj: ObjectRef) -> list[ObjectRef]:
        """Get objects that this object references (forward lookup)."""
        key = f"{obj.obj_type.value}:{obj.schema}.{obj.name}"
        return self.forward.get(key, [])

    def get_dependents(self, obj: ObjectRef) -> list[ObjectRef]:
        """Get objects that reference this object (reverse lookup)."""
        key = f"{obj.obj_type.value}:{obj.schema}.{obj.name}"
        return self.reverse.get(key, [])

    def get_dependents_by_name(self, schema: str, name: str) -> list[ObjectRef]:
        """Get all objects referencing schema.name regardless of target type.

        Useful for tables/views where you want to find all dependents
        without knowing if the target was registered as TABLE or VIEW.
        """
        results: list[ObjectRef] = []
        for key, sources in self.reverse.items():
            # key format: "TYPE:schema.name"
            _, qualified = key.split(":", 1)
            if qualified == f"{schema}.{name}":
                results.extend(sources)
        return results

    def get_edge_label(self, source: ObjectRef, target: ObjectRef) -> str:
        """Get the label for an edge between two objects (e.g., FK name)."""
        src_key = f"{source.obj_type.value}:{source.schema}.{source.name}"
        tgt_key = f"{target.obj_type.value}:{target.schema}.{target.name}"
        edge_key = f"{src_key}->{tgt_key}"
        return self.edge_labels.get(edge_key, "")


# --- Object Enumeration ---


def _enumerate_objects(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> list[tuple[ObjectRef, str]]:
    """Discover all database objects and their SQL definitions.

    Scans all schemas to find objects that may reference or be
    referenced by other objects.

    Args:
        connection: Active MySQL connection.

    Returns:
        List of (ObjectRef, sql_definition) tuples.
    """
    objects: list[tuple[ObjectRef, str]] = []

    objects.extend(
        _fetch_objects(connection, load_sql("browser/dep_views.sql"), ObjectType.VIEW, "enum.views")
    )
    objects.extend(
        _fetch_objects(
            connection,
            load_sql("browser/dep_procedures.sql"),
            ObjectType.PROCEDURE,
            "enum.procedures",
        )
    )
    objects.extend(
        _fetch_objects(
            connection,
            load_sql("browser/dep_functions.sql"),
            ObjectType.FUNCTION,
            "enum.functions",
        )
    )
    objects.extend(
        _fetch_objects(
            connection,
            load_sql("browser/dep_triggers.sql"),
            ObjectType.TRIGGER,
            "enum.triggers",
        )
    )
    objects.extend(
        _fetch_objects(
            connection, load_sql("browser/dep_events.sql"), ObjectType.EVENT, "enum.events"
        )
    )

    return objects


def _fetch_objects(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    sql: str,
    obj_type: ObjectType,
    log_label: str,
) -> list[tuple[ObjectRef, str]]:
    """Execute a query and return (ObjectRef, definition) pairs."""
    start = time.perf_counter()
    try:
        cursor = connection.cursor(buffered=True)
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
    except Exception:
        return []
    duration = time.perf_counter() - start
    log_sql(sql, duration, f"dependencies.{log_label}")

    results: list[tuple[ObjectRef, str]] = []
    for row in rows:
        schema = str(row[0] or "")  # type: ignore[index]
        name = str(row[1] or "")  # type: ignore[index]
        definition = str(row[2] or "")  # type: ignore[index]
        if schema and name:
            ref = ObjectRef(schema=schema, name=name, obj_type=obj_type)
            results.append((ref, definition))
    return results


def _enumerate_tables(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> list[ObjectRef]:
    """Discover all tables (they have no SQL definition to parse).

    Tables are targets only — other objects reference them.
    """
    sql = load_sql("browser/dep_tables.sql")
    start = time.perf_counter()
    try:
        cursor = connection.cursor(buffered=True)
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
    except Exception:
        return []
    duration = time.perf_counter() - start
    log_sql(sql, duration, "dependencies.enum.tables")

    return [
        ObjectRef(
            schema=str(row[0] or ""),  # type: ignore[index]
            name=str(row[1] or ""),  # type: ignore[index]
            obj_type=ObjectType.TABLE,
        )
        for row in rows
        if row[0] and row[1]  # type: ignore[index]
    ]


def _enumerate_foreign_keys(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> list[tuple[str, str, str, str, str]]:
    """Discover FK relationships.

    Returns: (source_schema, source_table, target_schema, target_table, constraint_name).
    """
    sql = load_sql("browser/dep_foreign_keys.sql")
    start = time.perf_counter()
    try:
        cursor = connection.cursor(buffered=True)
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
    except Exception:
        return []
    duration = time.perf_counter() - start
    log_sql(sql, duration, "dependencies.enum.fks")

    return [
        (
            str(row[0] or ""),  # type: ignore[index]
            str(row[1] or ""),  # type: ignore[index]
            str(row[2] or ""),  # type: ignore[index]
            str(row[3] or ""),  # type: ignore[index]
            str(row[4] or ""),  # type: ignore[index]
        )
        for row in rows
        if row[0] and row[1] and row[3]  # type: ignore[index]
    ]


# --- SQL Parser ---


def _parse_references(sql_definition: str, default_schema: str) -> list[str]:
    """Parse SQL definition and extract fully-qualified object references.

    Uses sqlglot with MySQL dialect. Resolves unqualified names using
    the default_schema from the object's context.

    Handles:
    - BEGIN/END block stripping (procedures, triggers, events)
    - CALL statements (extracted via regex since sqlglot can't parse them)
    - Standard DML (SELECT, INSERT, UPDATE, DELETE)

    Args:
        sql_definition: SQL body of the object.
        default_schema: Schema of the object being parsed (for name resolution).

    Returns:
        List of fully-qualified references as "schema.name" strings.
    """
    import re

    if not sql_definition or not sql_definition.strip():
        return []

    body = sql_definition.strip()

    # Strip BEGIN/END wrapper — sqlglot misparses it as Transaction/End
    body = re.sub(r"^\s*BEGIN\s+", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s+END\s*$", "", body, flags=re.IGNORECASE)

    references: set[str] = set()

    # Extract CALL statements before stripping (sqlglot can't parse them)
    for match in re.finditer(r"\bCALL\s+(?:`?(\w+)`?\.)?`?(\w+)`?\s*\(", body, re.IGNORECASE):
        call_schema = match.group(1) or default_schema
        call_name = match.group(2)
        references.add(f"{call_schema}.{call_name}")

    # Extract function calls: word( — before IF stripping removes conditions
    # MySQL built-in functions to ignore
    _builtins = {
        "concat",
        "concat_ws",
        "if",
        "ifnull",
        "nullif",
        "coalesce",
        "now",
        "curdate",
        "curtime",
        "date_add",
        "date_sub",
        "datediff",
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "second",
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "group_concat",
        "left",
        "right",
        "substring",
        "trim",
        "upper",
        "lower",
        "replace",
        "length",
        "char_length",
        "abs",
        "ceil",
        "floor",
        "round",
        "mod",
        "last_insert_id",
        "row_count",
        "found_rows",
        "cast",
        "convert",
        "date_format",
        "str_to_date",
        "isnull",
        "greatest",
        "least",
        "field",
        "find_in_set",
        "hex",
        "unhex",
        "md5",
        "sha1",
        "sha2",
        "uuid",
        "json_extract",
        "json_set",
        "json_replace",
        "json_remove",
        "json_object",
        "json_array",
        "json_contains",
        "json_length",
        "values",
        "default",
        "exists",
    }
    for match in re.finditer(r"\b(?:`?(\w+)`?\.)?`?(\w+)`?\s*\(", body):
        fn_schema = match.group(1)
        fn_name = match.group(2)
        if fn_name.lower() in _builtins:
            continue
        schema_resolved = fn_schema or default_schema
        references.add(f"{schema_resolved}.{fn_name}")

    # Strip MySQL procedural flow control that sqlglot cannot parse
    # Remove IF/ELSEIF conditions (keep the body inside)
    body = re.sub(r"\bIF\b\s+.+?\s+\bTHEN\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bELSEIF\b\s+.+?\s+\bTHEN\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bELSE\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bEND\s+IF\b", "", body, flags=re.IGNORECASE)
    # Remove CASE/WHEN/END CASE control
    body = re.sub(r"\bCASE\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bWHEN\b\s+.+?\s+\bTHEN\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bEND\s+CASE\b", "", body, flags=re.IGNORECASE)
    # Remove LOOP/WHILE/REPEAT control
    body = re.sub(r"\bWHILE\b\s+.+?\s+\bDO\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bEND\s+WHILE\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\b\w+\s*:\s*LOOP\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bLOOP\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bEND\s+LOOP\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bREPEAT\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bUNTIL\b\s+.+?\s+\bEND\s+REPEAT\b", "", body, flags=re.IGNORECASE)
    # Remove LEAVE/ITERATE labels
    body = re.sub(r"\bLEAVE\b\s+\w+", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bITERATE\b\s+\w+", "", body, flags=re.IGNORECASE)
    # Remove OPEN/CLOSE/FETCH cursor statements
    body = re.sub(r"\bOPEN\b\s+\w+", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bCLOSE\b\s+\w+", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bFETCH\b\s+\w+\s+INTO\b[^;]+", "", body, flags=re.IGNORECASE)
    # Remove DECLARE for variables and handlers (NOT cursors — those have SQL)
    body = re.sub(
        r"\bDECLARE\b\s+\w+\s+(INT|TINYINT|SMALLINT|BIGINT|DECIMAL|FLOAT|DOUBLE|"
        r"VARCHAR|CHAR|TEXT|DATE|DATETIME|TIMESTAMP|BOOLEAN|BLOB)\b[^;]*;",
        "",
        body,
        flags=re.IGNORECASE,
    )
    body = re.sub(
        r"\bDECLARE\b\s+(CONTINUE|EXIT)\s+HANDLER\b[^;]*;",
        "",
        body,
        flags=re.IGNORECASE,
    )
    # Transform DECLARE cursor: extract the SELECT inside
    body = re.sub(
        r"\bDECLARE\b\s+\w+\s+CURSOR\s+FOR\s+",
        "",
        body,
        flags=re.IGNORECASE,
    )
    # Remove standalone SET statements (variable assignments, not UPDATE ... SET)
    body = re.sub(
        r"^\s*SET\s+@?\w+\s*=[^;]+;",
        "",
        body,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    # Remove START TRANSACTION / COMMIT / ROLLBACK
    body = re.sub(r"\bSTART\s+TRANSACTION\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bCOMMIT\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bROLLBACK\b", "", body, flags=re.IGNORECASE)
    # Remove nested BEGIN/END (in handler blocks, nested blocks)
    body = re.sub(r"\bBEGIN\b", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\bEND\s*;", ";", body, flags=re.IGNORECASE)
    # Remove SELECT ... INTO var (converts to plain SELECT)
    body = re.sub(
        r"\bINTO\s+(?:@\w+|v_\w+)(?:\s*,\s*(?:@\w+|v_\w+))*",
        "",
        body,
        flags=re.IGNORECASE,
    )

    # Parse with sqlglot — try individual statements for resilience
    # Split on semicolons and parse each one, so a failure in one
    # statement doesn't prevent parsing the rest
    statements_text = [s.strip() for s in body.split(";") if s.strip()]

    for stmt_text in statements_text:
        try:
            parsed = sqlglot.parse(
                stmt_text, dialect="mysql", error_level=sqlglot.ErrorLevel.IGNORE
            )
        except Exception:
            continue

        for stmt in parsed:
            if stmt is None:
                continue
            for table in stmt.find_all(exp.Table):
                name = table.name
                if not name:
                    continue
                if name.upper() in ("DUAL",):
                    continue
                schema = table.db or default_schema
                qualified = f"{schema}.{name}"
                references.add(qualified)

    return list(references)


# --- Graph Builder ---


def build_dependency_graph(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> DependencyGraph:
    """Build the complete dependency graph for all user schemas.

    Scans all non-system schemas to discover objects and their relationships.

    Steps:
        1. Enumerate all tables (as targets).
        2. Enumerate views, procedures, functions, triggers, events with definitions.
        3. Parse each definition to extract references.
        4. Resolve names and build graph edges.
        5. Add FK-based dependencies.

    Args:
        connection: Active MySQL connection.

    Returns:
        Populated DependencyGraph.
    """
    graph = DependencyGraph()

    # 1. Register all tables
    tables = _enumerate_tables(connection)
    for table in tables:
        graph.add_object(table)

    # 2. Enumerate objects with definitions
    objects_with_defs = _enumerate_objects(connection)

    # Register all objects
    for obj, _ in objects_with_defs:
        graph.add_object(obj)

    # 3-4. Parse definitions and build edges
    for obj, definition in objects_with_defs:
        refs = _parse_references(definition, obj.schema)
        for ref_qualified in refs:
            parts = ref_qualified.split(".", 1)
            if len(parts) != 2:
                continue
            ref_schema, ref_name = parts

            # Skip self-references
            if ref_schema == obj.schema and ref_name == obj.name:
                continue

            # Find the target object — could be TABLE or VIEW
            target = _find_target(graph, ref_schema, ref_name)
            if target:
                graph.add_dependency(obj, target)

    # 5. Add FK dependencies (table → referenced table)
    fk_rels = _enumerate_foreign_keys(connection)
    for src_schema, src_table, tgt_schema, tgt_table, fk_name in fk_rels:
        source = _find_target(graph, src_schema, src_table)
        target = _find_target(graph, tgt_schema, tgt_table)
        if source and target and source != target:
            graph.add_dependency(source, target, label=f"FK: {fk_name}")

    return graph


def _find_target(graph: DependencyGraph, schema: str, name: str) -> ObjectRef | None:
    """Find an object in the graph by schema and name.

    Checks TABLE first, then VIEW (since both can be referenced in FROM clauses).
    """
    for obj_type in (ObjectType.TABLE, ObjectType.VIEW, ObjectType.PROCEDURE, ObjectType.FUNCTION):
        key = f"{obj_type.value}:{schema}.{name}"
        if key in graph.objects:
            return graph.objects[key]
    return None
