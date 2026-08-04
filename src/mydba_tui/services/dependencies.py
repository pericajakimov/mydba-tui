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

    def add_dependency(
        self, source: ObjectRef, target: ObjectRef, label: str = ""
    ) -> None:
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

    # Views
    sql = (
        "SELECT table_schema, table_name, view_definition "
        "FROM information_schema.views"
    )
    objects.extend(_fetch_objects(connection, sql, ObjectType.VIEW, "enum.views"))

    # Procedures
    sql = (
        "SELECT routine_schema, routine_name, routine_definition "
        "FROM information_schema.routines "
        "WHERE routine_type = 'PROCEDURE'"
    )
    objects.extend(_fetch_objects(connection, sql, ObjectType.PROCEDURE, "enum.procedures"))

    # Functions
    sql = (
        "SELECT routine_schema, routine_name, routine_definition "
        "FROM information_schema.routines "
        "WHERE routine_type = 'FUNCTION'"
    )
    objects.extend(_fetch_objects(connection, sql, ObjectType.FUNCTION, "enum.functions"))

    # Triggers
    sql = (
        "SELECT trigger_schema, trigger_name, action_statement "
        "FROM information_schema.triggers"
    )
    objects.extend(_fetch_objects(connection, sql, ObjectType.TRIGGER, "enum.triggers"))

    # Events
    sql = (
        "SELECT event_schema, event_name, event_definition "
        "FROM information_schema.events"
    )
    objects.extend(_fetch_objects(connection, sql, ObjectType.EVENT, "enum.events"))

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
    sql = (
        "SELECT table_schema, table_name "
        "FROM information_schema.tables "
        "WHERE table_type = 'BASE TABLE'"
    )
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
    sql = (
        "SELECT constraint_schema, table_name, "
        "constraint_schema, referenced_table_name, constraint_name "
        "FROM information_schema.referential_constraints"
    )
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
    """Parse SQL definition and extract fully-qualified table/view references.

    Uses sqlglot with MySQL dialect. Resolves unqualified names using
    the default_schema from the object's context.

    Args:
        sql_definition: SQL body of the object.
        default_schema: Schema of the object being parsed (for name resolution).

    Returns:
        List of fully-qualified references as "schema.name" strings.
    """
    if not sql_definition or not sql_definition.strip():
        return []

    try:
        statements = sqlglot.parse(
            sql_definition, dialect="mysql", error_level=sqlglot.ErrorLevel.IGNORE
        )
    except Exception:
        return []

    references: set[str] = set()
    for stmt in statements:
        if stmt is None:
            continue
        for table in stmt.find_all(exp.Table):
            name = table.name
            if not name:
                continue
            # Skip aliases and subquery references
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
