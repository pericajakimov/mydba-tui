"""
Main workspace screen.

The primary interface after connecting to a database.
Split-pane layout: object browser tree on the left,
tabbed metadata/content area on the right.
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static, TabbedContent, TabPane, Tree
from textual.widgets.tree import TreeNode

from mydba_tui.ui.widgets import StatusBar


class MainWorkspaceScreen(Screen[None]):
    """Main workspace with split-pane layout."""

    BINDINGS = [
        Binding("c", "open_profiles", "Connections", key_display="C"),
        Binding("r", "refresh", "Refresh", key_display="R"),
        Binding("f6", "switch_focus", "Switch Panel", key_display="F6"),
        Binding("f10", "quit", "Exit", key_display="F10"),
    ]

    CSS = """
    #workspace-layout {
        layout: horizontal;
        height: 1fr;
    }

    #browser-panel {
        width: 48;
        min-width: 30;
        border-right: solid $panel-darken-1;
        overflow-y: auto;
    }

    #browser-tree {
        width: 100%;
    }

    #content-panel {
        width: 1fr;
    }

    #metadata-tabs {
        height: 1fr;
    }

    ContentSwitcher {
        height: 1fr;
    }

    TabPane {
        height: 1fr;
    }

    TabPane > VerticalScroll {
        height: 100%;
    }

    .tab-content {
        padding: 1 2;
    }

    #object-header {
        padding: 0 1;
        height: 1;
    }

    .sample-buttons {
        height: 3;
        padding: 0 1;
    }

    #sample-scroll {
        height: 1fr;
    }

    .sample-buttons Button {
        margin-right: 1;
    }
    """

    def __init__(self) -> None:
        """Initialize the workspace."""
        super().__init__()
        self._selected_schema: str = ""
        self._selected_object: str = ""
        self._selected_category: str = ""
        self._focus_on_tree: bool = True
        # Cached metadata for the currently selected table
        self._table_info: Any = None
        self._table_columns: Any = None
        self._table_indexes: Any = None
        self._table_index_sizes: dict[str, int] = {}
        self._table_fk_outgoing: Any = None
        self._table_fk_incoming: Any = None
        self._table_triggers: Any = None
        self._table_partitions: Any = None
        self._table_grants: Any = None
        self._table_ddl: str = ""
        # Dependency graph (schema-wide, persists across table selections)
        self._dep_graph: Any = None

    def compose(self) -> ComposeResult:
        """Build the split-pane layout."""
        yield Header()
        yield StatusBar(id="status-bar")

        with Horizontal(id="workspace-layout"):
            with Vertical(id="browser-panel"):
                yield Tree("Schemas", id="browser-tree")
            with Vertical(id="content-panel"):
                yield Static(
                    "[dim]Select an object from the browser to view its metadata.[/dim]",
                )

        yield Footer()

    def on_mount(self) -> None:
        """Load schemas into the tree on mount."""
        self._sync_status_bar()
        self._load_schemas()
        self._build_dependency_graph()
        self.query_one("#browser-tree", Tree).focus()

    def on_screen_resume(self) -> None:
        """Update status bar and reload schemas when returning to this screen."""
        self._sync_status_bar()
        self._load_schemas()
        self._reset_content_panel()
        self._build_dependency_graph()

    def _sync_status_bar(self) -> None:
        """Sync status bar with current connection state."""
        status = getattr(self.app, "connection_status", "")
        if status:
            self.query_one("#status-bar", StatusBar).status_text = status

    def _reset_content_panel(self) -> None:
        """Reset the content panel to initial state and clear cached data."""
        self._selected_schema = ""
        self._selected_object = ""
        self._selected_category = ""
        self._table_info = None
        self._table_columns = None
        self._table_indexes = None
        self._table_index_sizes = {}
        self._table_fk_outgoing = None
        self._table_fk_incoming = None
        self._table_triggers = None
        self._table_partitions = None
        self._table_grants = None
        self._table_ddl = ""
        self._dep_graph = None

        content_panel = self.query_one("#content-panel", Vertical)
        content_panel.remove_children()
        content_panel.mount(
            Static(
                "[dim]Select an object from the browser to view its metadata.[/dim]",
            )
        )

    def _load_schemas(self) -> None:
        """Load schema list from the database into the tree."""
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.services.browser import get_schemas

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            return

        try:
            schemas = get_schemas(conn_result.connection)
        except Exception:
            self.notify("Failed to load schemas.", severity="error")
            return

        tree = self.query_one("#browser-tree", Tree)
        tree.clear()
        tree.root.expand()

        for schema in schemas:
            node = tree.root.add(schema, data={"type": "schema", "name": schema, "loaded": False})
            node.allow_expand = True

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[object]) -> None:
        """Handle expansion of a tree node — lazy load children."""
        node = event.node
        data = node.data
        if not isinstance(data, dict):
            return

        if data.get("type") == "schema" and not data.get("loaded"):
            self._load_object_types(node)
        elif data.get("type") == "category" and not data.get("loaded"):
            self._load_objects(node)

    def _load_object_types(self, schema_node: TreeNode[object]) -> None:
        """Load object type categories for a schema node."""
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.services.browser import get_object_counts

        data = schema_node.data
        if not isinstance(data, dict):
            return

        schema_name = data["name"]
        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            return

        try:
            counts = get_object_counts(conn_result.connection, schema_name)
        except Exception:
            self.notify(f"Failed to load objects for {schema_name}.", severity="error")
            return

        data["loaded"] = True

        categories = [
            ("Tables", counts.tables, "tables"),
            ("Views", counts.views, "views"),
            ("Procedures", counts.procedures, "procedures"),
            ("Functions", counts.functions, "functions"),
            ("Events", counts.events, "events"),
            ("Triggers", counts.triggers, "triggers"),
        ]
        for label, count, category in categories:
            cat_node = schema_node.add(
                f"{label} ({count})",
                data={
                    "type": "category",
                    "category": category,
                    "schema": schema_name,
                    "loaded": False,
                },
            )
            cat_node.allow_expand = True

    def _load_objects(self, category_node: TreeNode[object]) -> None:
        """Load individual objects for a category node."""
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.services.browser import get_objects

        data = category_node.data
        if not isinstance(data, dict):
            return

        schema = data["schema"]
        category = data["category"]

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            return

        try:
            objects = get_objects(conn_result.connection, schema, category)
        except Exception:
            self.notify(f"Failed to load {category}.", severity="error")
            return

        data["loaded"] = True

        for obj_name in objects:
            category_node.add_leaf(
                obj_name,
                data={
                    "type": "object",
                    "category": category,
                    "schema": schema,
                    "name": obj_name,
                },
            )

    def on_tree_node_selected(self, event: Tree.NodeSelected[object]) -> None:
        """Handle selection of a tree node."""
        node = event.node
        data = node.data
        if not isinstance(data, dict):
            return

        if data.get("type") == "schema":
            schema_name = data["name"]
            self._show_placeholder(
                f"[bold cyan]{schema_name}[/bold cyan]\n\n[dim]Expand to browse objects.[/dim]"
            )
        elif data.get("type") == "category":
            schema = data["schema"]
            category = data["category"]
            self._show_placeholder(
                f"[bold cyan]{schema}[/bold cyan] — {category.capitalize()}\n\n"
                f"[dim]Expand to list objects.[/dim]"
            )
        elif data.get("type") == "object":
            schema = data["schema"]
            category = data["category"]
            name = data["name"]
            self._selected_schema = schema
            self._selected_object = name
            self._selected_category = category
            if category == "tables":
                self._show_table_tabs(schema, name)
            else:
                self._show_placeholder(
                    f"[bold cyan]{schema}.{name}[/bold cyan]"
                    f" [dim]({category[:-1]})[/dim]\n\n"
                    f"[dim]Metadata view for {category} coming soon.[/dim]"
                )

    def _show_placeholder(self, text: str) -> None:
        """Show simple text in the content panel (no tabs)."""
        content_panel = self.query_one("#content-panel", Vertical)
        content_panel.remove_children()
        content_panel.mount(Static(text))

    def _show_table_tabs(self, schema: str, table: str) -> None:
        """Load all table metadata and show tabbed view."""
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.services.browser import (
            get_index_sizes,
            get_table_columns,
            get_table_fk_incoming,
            get_table_fk_outgoing,
            get_table_grants,
            get_table_indexes,
            get_table_info,
            get_table_partitions,
            get_table_triggers,
        )

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            return

        # Load all metadata at once
        try:
            self._table_info = get_table_info(conn_result.connection, schema, table)
            self._table_columns = get_table_columns(conn_result.connection, schema, table)
            self._table_indexes = get_table_indexes(conn_result.connection, schema, table)
            self._table_index_sizes = get_index_sizes(conn_result.connection, schema, table)
            self._table_fk_outgoing = get_table_fk_outgoing(conn_result.connection, schema, table)
            self._table_fk_incoming = get_table_fk_incoming(conn_result.connection, schema, table)
            self._table_triggers = get_table_triggers(conn_result.connection, schema, table)
            self._table_partitions = get_table_partitions(conn_result.connection, schema, table)
            self._table_grants = get_table_grants(conn_result.connection, schema, table)
        except Exception as e:
            self._show_placeholder(f"[red]Error loading metadata: {e}[/red]")
            return

        # Load DDL
        import time

        from mydba_tui.logging import log_sql

        sql = f"SHOW CREATE TABLE `{schema}`.`{table}`"
        start = time.perf_counter()
        try:
            cursor = conn_result.connection.cursor(buffered=True)
            cursor.execute(sql)
            row = cursor.fetchone()
            cursor.close()
            duration = time.perf_counter() - start
            log_sql(sql, duration, "browser.ddl")
            self._table_ddl = str(row[1]) if row and len(row) >= 2 else ""  # type: ignore[index]
        except Exception:
            self._table_ddl = ""

        # Show tabs and render the first one
        content_panel = self.query_one("#content-panel", Vertical)
        content_panel.remove_children()
        container = _TableMetadataTabs(schema, table)
        content_panel.mount(container)

        # Render the General tab immediately
        self.call_after_refresh(self._render_general_tab)

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Render tab content from cached data."""
        if not self._selected_schema or not self._selected_object:
            return

        pane_id = event.pane.id

        if pane_id == "tab-general":
            self._render_general_tab()
        elif pane_id == "tab-columns":
            self._render_columns_tab()
        elif pane_id == "tab-indexes":
            self._render_indexes_tab()
        elif pane_id == "tab-fk":
            self._render_fk_tab()
        elif pane_id == "tab-triggers":
            self._render_triggers_tab()
        elif pane_id == "tab-partitions":
            self._render_partitions_tab()
        elif pane_id == "tab-grants":
            self._render_grants_tab()
        elif pane_id == "tab-deps":
            self._render_dependencies_tab()
        elif pane_id == "tab-sample":
            self._update_sample_results(
                "[dim]Click a button above to load sample data.[/dim]"
            )
        elif pane_id == "tab-ddl":
            self._render_ddl_tab()

    def _render_general_tab(self) -> None:
        """Render general info from cached data."""
        from mydba_tui.services.browser import TableInfo

        info = self._table_info
        if not isinstance(info, TableInfo):
            return

        total_size = info.data_size + info.index_size
        frag_pct = f"{(info.data_free / total_size * 100):.1f}%" if total_size > 0 else "0%"

        lines: list[str] = []
        lines.append(f"        [dim]Engine:[/dim] {info.engine}")
        lines.append(f"    [dim]Row Format:[/dim] {info.row_format}")
        lines.append(f"[dim] Rows (approx):[/dim] {info.row_count:,}")
        lines.append(f"[dim]Avg Row Length:[/dim] {info.avg_row_length:,} bytes")
        lines.append(f"     [dim]Data Size:[/dim] {_format_bytes(info.data_size):>10}")
        lines.append(f"    [dim]Index Size:[/dim] {_format_bytes(info.index_size):>10}")
        lines.append(f"    [dim]Total Size:[/dim] {_format_bytes(total_size):>10}")
        lines.append(f"    [dim]Free Space:[/dim] {_format_bytes(info.data_free):>10}")
        lines.append(f" [dim]Fragmentation:[/dim] {frag_pct}")
        lines.append(
            f"[dim]Auto Increment:[/dim] {info.auto_increment:,}"
            if info.auto_increment is not None
            else "[dim]Auto Increment:[/dim]"
        )
        lines.append(f"     [dim]Collation:[/dim] {info.collation}")
        lines.append(f"[dim]Create Options:[/dim] {info.create_options or ''}")
        lines.append(f"       [dim]Created:[/dim] {info.create_time}")
        lines.append(f"       [dim]Updated:[/dim] {info.update_time or ''}")
        lines.append(f"       [dim]Checked:[/dim] {info.check_time or ''}")
        lines.append(f"       [dim]Comment:[/dim] {info.comment or ''}")

        self._update_tab("tab-general", "\n".join(lines))

    def _render_columns_tab(self) -> None:
        """Render columns from cached data."""
        columns = self._table_columns
        if columns is None:
            return

        if not columns:
            self._update_tab("tab-columns", "[dim]No columns found.[/dim]")
            return

        from mydba_tui.services.browser import ColumnInfo

        cols = [c for c in columns if isinstance(c, ColumnInfo)]

        # Dynamic column width for Type
        max_type_len = max(len(col.col_type) for col in cols)
        type_width = max(max_type_len + 2, 15)

        lines: list[str] = []
        lines.append(
            f"[bold]{'#':<4}{'Name':<32}{'Type':<{type_width}}{'Null':<6}{'Key':<5}{'Extra'}[/bold]"
        )
        lines.append(f"{'─' * 4}{'─' * 32}{'─' * type_width}{'─' * 6}{'─' * 5}{'─' * 20}")
        for col in cols:
            nullable = "YES" if col.nullable == "YES" else "NO"
            if col.key == "PRI":
                key_display = "[bold green]PRI[/bold green]"
            elif col.key == "UNI":
                key_display = "[green]UNI[/green]"
            elif col.key == "MUL":
                key_display = "[cyan]MUL[/cyan]"
            else:
                key_display = ""
            lines.append(
                f"{col.position:<4}{col.name:<32}"
                f"[dim]{col.col_type:<{type_width}}[/dim]"
                f"{nullable:<6}{key_display:<5} {col.extra}"
            )

        self._update_tab("tab-columns", "\n".join(lines))

    def _render_indexes_tab(self) -> None:
        """Render indexes from cached data."""
        from mydba_tui.services.browser import IndexInfo, TableInfo

        indexes = self._table_indexes
        info = self._table_info
        index_sizes = self._table_index_sizes

        if indexes is None:
            return
        if not indexes:
            self._update_tab("tab-indexes", "[dim]No indexes.[/dim]")
            return

        idxs = [i for i in indexes if isinstance(i, IndexInfo)]
        row_count = info.row_count if isinstance(info, TableInfo) else 0

        lines: list[str] = []

        # Group by index name, PRIMARY first
        index_names: list[str] = []
        seen: set[str] = set()
        for idx in idxs:
            if idx.name not in seen:
                seen.add(idx.name)
                index_names.append(idx.name)

        index_names.sort(key=lambda n: (0 if n == "PRIMARY" else 1, n))

        for idx_name in index_names:
            idx_entries = [i for i in idxs if i.name == idx_name]
            first = idx_entries[0]

            # Build columns list
            cols_parts = []
            for entry in idx_entries:
                col_display = entry.expression if entry.expression else entry.column
                cols_parts.append(col_display)
            cols_str = ", ".join(cols_parts)

            # Index header
            if idx_name == "PRIMARY":
                prefix = "[bold green]PRIMARY[/bold green]"
            elif first.non_unique == 0:
                prefix = f"[green]UNIQUE[/green] {idx_name}"
            else:
                prefix = idx_name

            vis_flag = " — [dim]INVISIBLE[/dim]" if first.visible == "NO" else ""
            lines.append(f"{prefix} [dim]({first.index_type}){vis_flag}[/dim]")
            lines.append(f"  Columns: [cyan]{cols_str}[/cyan]")

            # Cardinality and selectivity
            last_entry = idx_entries[-1]
            if last_entry.cardinality > 0:
                card_str = f"{last_entry.cardinality:,}"
                if row_count > 0:
                    selectivity = last_entry.cardinality / row_count * 100
                    sel_str = f"{selectivity:.1f}%"
                    if selectivity < 1.0 and idx_name != "PRIMARY":
                        card_str += f" [dim](selectivity: {sel_str})[/dim] [yellow]⚠ low[/yellow]"
                    else:
                        card_str += f" [dim](selectivity: {sel_str})[/dim]"
                lines.append(f"  Cardinality: {card_str}")

            # Index size (from innodb_index_stats)
            if idx_name in index_sizes:
                size_str = _format_bytes(index_sizes[idx_name])
                lines.append(f"  Size: {size_str}")

            if first.comment:
                lines.append(f"  Comment: {first.comment}")

            lines.append("")

        self._update_tab("tab-indexes", "\n".join(lines))

    def _render_fk_tab(self) -> None:
        """Render foreign keys from cached data."""
        from mydba_tui.services.browser import ForeignKeyInfo

        outgoing = self._table_fk_outgoing
        incoming = self._table_fk_incoming
        table = self._selected_object

        if outgoing is None and incoming is None:
            return

        out_fks = [fk for fk in (outgoing or []) if isinstance(fk, ForeignKeyInfo)]
        in_fks = [fk for fk in (incoming or []) if isinstance(fk, ForeignKeyInfo)]

        if not out_fks and not in_fks:
            self._update_tab("tab-fk", "[dim]No foreign keys.[/dim]")
            return

        lines: list[str] = []

        # --- Outgoing: this table's FK constraints ---
        if out_fks:
            lines.append("[bold]References[/bold]\n")

            # Group by constraint name
            constraint_names: list[str] = []
            seen: set[str] = set()
            for fk in out_fks:
                if fk.constraint_name not in seen:
                    seen.add(fk.constraint_name)
                    constraint_names.append(fk.constraint_name)

            for cname in constraint_names:
                entries = [fk for fk in out_fks if fk.constraint_name == cname]
                first = entries[0]

                # Arrow line: col1, col2 → target(col1, col2)
                src_cols = ", ".join(e.column for e in entries)
                ref_cols = ", ".join(e.referenced_column for e in entries)
                lines.append(
                    f"[cyan]{src_cols}[/cyan] → "
                    f"[cyan]{first.referenced_table}[/cyan]({ref_cols})"
                )

                # DDL-style breakdown (dimmed)
                fk_cols = ", ".join(f"`{e.column}`" for e in entries)
                ref_cols_q = ", ".join(f"`{e.referenced_column}`" for e in entries)
                lines.append(f"  [dim]CONSTRAINT `{cname}`[/dim]")
                lines.append(f"    [dim]FOREIGN KEY ({fk_cols})[/dim]")
                lines.append(
                    f"    [dim]REFERENCES `{first.referenced_table}` ({ref_cols_q})[/dim]"
                )
                lines.append(
                    f"    [dim]ON DELETE {first.delete_rule} "
                    f"ON UPDATE {first.update_rule}[/dim]"
                )
                lines.append("")

        # --- Incoming: other tables referencing this table ---
        if in_fks:
            if out_fks:
                lines.append("")
            lines.append("[bold]Referenced By[/bold]\n")

            # Group by constraint name
            constraint_names = []
            seen = set()
            for fk in in_fks:
                if fk.constraint_name not in seen:
                    seen.add(fk.constraint_name)
                    constraint_names.append(fk.constraint_name)

            for cname in constraint_names:
                entries = [fk for fk in in_fks if fk.constraint_name == cname]
                first = entries[0]

                # Arrow line: source_table(col1, col2) → this_col1, this_col2
                src_cols = ", ".join(e.column for e in entries)
                ref_cols = ", ".join(e.referenced_column for e in entries)
                lines.append(
                    f"[cyan]{first.source_table}[/cyan]({src_cols}) → "
                    f"[cyan]{ref_cols}[/cyan]"
                )

                # DDL-style breakdown (dimmed)
                fk_cols = ", ".join(f"`{e.column}`" for e in entries)
                ref_cols_q = ", ".join(f"`{e.referenced_column}`" for e in entries)
                lines.append(f"  [dim]CONSTRAINT `{cname}`[/dim]")
                lines.append(f"    [dim]FOREIGN KEY ({fk_cols})[/dim]")
                lines.append(
                    f"    [dim]REFERENCES `{table}` ({ref_cols_q})[/dim]"
                )
                lines.append(
                    f"    [dim]ON DELETE {first.delete_rule} "
                    f"ON UPDATE {first.update_rule}[/dim]"
                )
                lines.append("")

        self._update_tab("tab-fk", "\n".join(lines))

    def _render_triggers_tab(self) -> None:
        """Render triggers from cached data."""
        from mydba_tui.services.browser import TriggerInfo

        triggers = self._table_triggers

        if triggers is None:
            return
        if not triggers:
            self._update_tab("tab-triggers", "[dim]No triggers.[/dim]")
            return

        trigs = [t for t in triggers if isinstance(t, TriggerInfo)]
        lines: list[str] = []

        for i, trg in enumerate(trigs):
            if i > 0:
                lines.append("[dim]─────────────────────────────────────────[/dim]")
                lines.append("")
            # Header: name (TIMING EVENT)
            lines.append(
                f"[bold cyan]{trg.name}[/bold cyan] [dim]({trg.timing} {trg.event})[/dim]"
            )
            lines.append(f"  [dim]Definer:[/dim] {trg.definer}")
            lines.append(f"  [dim]Created:[/dim] {trg.created}")
            lines.append("")
            # Body as raw text, indented
            for body_line in trg.body.splitlines():
                lines.append(f"  {body_line}")
            lines.append("")

        self._update_tab("tab-triggers", "\n".join(lines))

    def _render_partitions_tab(self) -> None:
        """Render partitions from cached data."""
        from mydba_tui.services.browser import PartitionInfo

        partitions = self._table_partitions

        if partitions is None:
            return
        if not partitions:
            self._update_tab("tab-partitions", "[dim]Table is not partitioned.[/dim]")
            return

        parts = [p for p in partitions if isinstance(p, PartitionInfo)]
        if not parts:
            self._update_tab("tab-partitions", "[dim]Table is not partitioned.[/dim]")
            return

        lines: list[str] = []

        # Method and expression (table-level, same for all partitions)
        first = parts[0]
        lines.append(f"    [dim]Method:[/dim] {first.method}")
        lines.append(f"[dim]Expression:[/dim] {first.expression}")
        lines.append("")

        # Dynamic column widths
        max_name = max(len(p.name) for p in parts)
        name_w = max(max_name + 2, 10)
        max_desc = max(len(p.description) for p in parts)
        desc_w = max(max_desc + 2, 13)

        # Table header
        hdr = (
            f"{'#':<4}{'Name':<{name_w}}{'Description':<{desc_w}}"
            f"{'Rows':>10}  {'Data Size':>10}  {'Index Size':>10}  {'Total':>10}"
        )
        lines.append(f"[bold]{hdr}[/bold]")
        sep = (
            f"{'─' * 3} {'─' * (name_w - 1)} {'─' * (desc_w - 1)}"
            f" {'─' * 10}  {'─' * 10}  {'─' * 10}  {'─' * 10}"
        )
        lines.append(sep)

        # Rows
        for p in parts:
            total = p.data_size + p.index_size
            lines.append(
                f"{p.ordinal:<4}{p.name:<{name_w}}{p.description:<{desc_w}}"
                f"{p.row_count:>10,}  {_format_bytes(p.data_size):>10}"
                f"  {_format_bytes(p.index_size):>10}  {_format_bytes(total):>10}"
            )

        self._update_tab("tab-partitions", "\n".join(lines))

    def _render_grants_tab(self) -> None:
        """Render table grants from cached data."""
        from mydba_tui.services.browser import GrantInfo

        grants = self._table_grants

        if grants is None:
            return
        if not grants:
            self._update_tab("tab-grants", "[dim]No grants.[/dim]")
            return

        grs = [g for g in grants if isinstance(g, GrantInfo)]
        if not grs:
            self._update_tab("tab-grants", "[dim]No grants.[/dim]")
            return

        lines: list[str] = []

        # Dynamic column widths
        max_user_len = max(len(f"{g.user}@{g.host}") for g in grs)
        user_w = max(max_user_len + 2, 20)
        level_w = 8  # "GLOBAL" is longest at 6 + padding

        # Header
        lines.append(
            f"[bold]{'User':<{user_w}}{'Level':<{level_w}}Privileges[/bold]"
        )
        lines.append(
            f"{'─' * (user_w - 1)} {'─' * (level_w - 1)} {'─' * 40}"
        )

        # Rows
        for g in grs:
            user_display = f"{g.user}@{g.host}"
            level = g.grant_level
            privs = g.privileges.upper() if g.privileges else ""
            lines.append(f"{user_display:<{user_w}}[dim]{level:<{level_w}}[/dim]{privs}")

        self._update_tab("tab-grants", "\n".join(lines))

    def _render_dependencies_tab(self) -> None:
        """Render dependencies from the cached dependency graph."""
        from mydba_tui.services.dependencies import (
            DependencyGraph,
            ObjectRef,
            ObjectType,
        )

        graph = self._dep_graph
        schema = self._selected_schema
        table = self._selected_object

        if not schema or not table:
            return

        if not isinstance(graph, DependencyGraph):
            self._update_tab(
                "tab-deps",
                "[dim]Dependency graph not built yet.\n\n"
                "Use Refresh (r) to build the dependency graph.[/dim]",
            )
            return

        # Find this object in the graph
        current_ref: ObjectRef | None = None
        for otype in (ObjectType.TABLE, ObjectType.VIEW):
            key = f"{otype.value}:{schema}.{table}"
            if key in graph.objects:
                current_ref = graph.objects[key]
                break

        lines: list[str] = []

        # --- Section 1: Objects that this object depends on (forward) ---
        depends_on: list[ObjectRef] = []
        if current_ref:
            depends_on = graph.get_dependencies(current_ref)

        if depends_on:
            lines.append(
                f"[bold][yellow]{schema}[/yellow].[cyan]{table}[/cyan]"
                f" depends on:[/bold]\n"
            )

            # Group by type
            fwd_by_type: dict[str, list[tuple[str, str, str]]] = {}
            for dep in depends_on:
                type_label = dep.obj_type.value
                if type_label not in fwd_by_type:
                    fwd_by_type[type_label] = []
                label = ""
                if current_ref:
                    label = graph.get_edge_label(current_ref, dep)
                entry = (dep.schema, dep.name, label)
                if entry not in fwd_by_type[type_label]:
                    fwd_by_type[type_label].append(entry)

            type_order = ["TABLE", "VIEW", "PROCEDURE", "FUNCTION", "TRIGGER", "EVENT"]
            for type_label in sorted(
                fwd_by_type.keys(),
                key=lambda t: type_order.index(t) if t in type_order else 99,
            ):
                entries = sorted(fwd_by_type[type_label])
                lines.append(f"  [bold]{type_label}[/bold] ({len(entries)})")
                for dep_schema, dep_name, label in entries:
                    line = (
                        f"    [yellow]{dep_schema}[/yellow]"
                        f".[cyan]{dep_name}[/cyan]"
                    )
                    if label:
                        line += f" [dim]({label})[/dim]"
                    lines.append(line)
                lines.append("")

        # --- Section 2: Objects depending on this object (reverse) ---
        dependents = graph.get_dependents_by_name(schema, table)

        if dependents:
            if depends_on:
                lines.append("")
            lines.append(
                f"[bold]Objects depending on "
                f"[yellow]{schema}[/yellow].[cyan]{table}[/cyan]:[/bold]\n"
            )

            rev_by_type: dict[str, list[tuple[str, str, str]]] = {}
            for dep in dependents:
                type_label = dep.obj_type.value
                if type_label not in rev_by_type:
                    rev_by_type[type_label] = []
                label = ""
                if current_ref:
                    label = graph.get_edge_label(dep, current_ref)
                entry = (dep.schema, dep.name, label)
                if entry not in rev_by_type[type_label]:
                    rev_by_type[type_label].append(entry)

            type_order = ["VIEW", "PROCEDURE", "FUNCTION", "TRIGGER", "EVENT", "TABLE"]
            for type_label in sorted(
                rev_by_type.keys(),
                key=lambda t: type_order.index(t) if t in type_order else 99,
            ):
                entries = sorted(rev_by_type[type_label])
                lines.append(f"  [bold]{type_label}[/bold] ({len(entries)})")
                for dep_schema, dep_name, label in entries:
                    line = (
                        f"    [yellow]{dep_schema}[/yellow]"
                        f".[cyan]{dep_name}[/cyan]"
                    )
                    if label:
                        line += f" [dim]({label})[/dim]"
                    lines.append(line)
                lines.append("")

        if not depends_on and not dependents:
            self._update_tab(
                "tab-deps",
                f"[dim]No dependencies found for [/dim]"
                f"[yellow]{schema}[/yellow].[cyan]{table}[/cyan]",
            )
            return

        self._update_tab("tab-deps", "\n".join(lines))

    def _render_ddl_tab(self) -> None:
        """Render DDL from cached data."""
        if self._table_ddl:
            self._update_tab("tab-ddl", self._table_ddl)
        else:
            self._update_tab("tab-ddl", "[dim]No DDL available.[/dim]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle sample data button clicks."""
        if event.button.id not in ("btn-sample-first", "btn-sample-last"):
            return

        from mydba_tui.connection import ConnectionResult
        from mydba_tui.services.browser import ColumnInfo, get_sample_data

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            return

        schema = self._selected_schema
        table = self._selected_object
        if not schema or not table:
            return

        # Get cached column metadata for smart SQL generation
        columns = [
            c for c in (self._table_columns or []) if isinstance(c, ColumnInfo)
        ]

        order = "ASC" if event.button.id == "btn-sample-first" else "DESC"

        try:
            col_names, rows = get_sample_data(
                conn_result.connection, schema, table, columns=columns,
                order=order, limit=5,
            )
        except Exception as e:
            self._update_sample_results(f"[red]Error: {e}[/red]")
            return

        if not rows:
            self._update_sample_results("[dim]No rows returned.[/dim]")
            return

        # Build vertical \G-style output
        label = "First" if order == "ASC" else "Last"
        max_name_len = max(len(name) for name in col_names)
        lines: list[str] = []
        lines.append(f"[dim]{label} {len(rows)} rows:[/dim]\n")

        for row_num, row in enumerate(rows, 1):
            lines.append(
                f"[bold]{'*' * 27} {row_num}. row {'*' * 27}[/bold]"
            )
            for i, val in enumerate(row):
                name = col_names[i]
                if val == "NULL":
                    val_str = "[dim]NULL[/dim]"
                elif val == "<binary>":
                    val_str = "[dim]<binary>[/dim]"
                else:
                    val_str = val
                lines.append(f"{name:>{max_name_len}}: {val_str}")
            lines.append("")

        self._update_sample_results("\n".join(lines))

    def _update_sample_results(self, content: str) -> None:
        """Update the sample data results area."""
        try:
            results = self.query_one("#sample-results", Static)
            results.update(content)
        except Exception:
            pass

    def _update_tab(self, tab_id: str, content: str) -> None:
        """Update the content of a tab pane by ID."""
        try:
            pane = self.query_one(f"#{tab_id}", TabPane)
            pane.remove_children()
            scroll = VerticalScroll(Static(content, classes="tab-content"))
            scroll.styles.height = "100%"
            pane.mount(scroll)
        except Exception:
            pass

    def action_switch_focus(self) -> None:
        """Switch focus between browser tree and content panel."""
        self._focus_on_tree = not self._focus_on_tree
        if self._focus_on_tree:
            self.query_one("#browser-tree", Tree).focus()
        else:
            try:
                tabs = self.query_one("#metadata-tabs", TabbedContent)
                tabs.focus()
            except Exception:
                pass

    def action_open_profiles(self) -> None:
        """Navigate to Connection Profiles."""
        self.app.push_screen("profiles")

    def action_refresh(self) -> None:
        """Rebuild the dependency graph without collapsing the object tree."""
        self._build_dependency_graph()

    def _build_dependency_graph(self) -> None:
        """Build (or rebuild) the dependency graph from all schemas."""
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.services.dependencies import build_dependency_graph

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            return

        self.notify("Building dependency graph...", severity="information")

        try:
            self._dep_graph = build_dependency_graph(conn_result.connection)
            dep_count = sum(len(v) for v in self._dep_graph.forward.values())
            self.notify(
                f"Dependency graph built: {len(self._dep_graph.objects)} objects, "
                f"{dep_count} dependencies.",
                severity="information",
            )
        except Exception as e:
            self.notify(f"Failed to build dependency graph: {e}", severity="error")

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()


class _TableMetadataTabs(Vertical):
    """Widget containing the tabbed metadata view for a table."""

    def __init__(self, schema: str, table: str) -> None:
        super().__init__()
        self._schema = schema
        self._table = table
        self.styles.height = "1fr"

    def compose(self) -> ComposeResult:
        yield Static(
            f"[bold cyan]{self._schema}.{self._table}[/bold cyan] [dim](table)[/dim]",
            id="object-header",
        )
        with TabbedContent(id="metadata-tabs"):
            with TabPane("General", id="tab-general"):
                yield Static("Loading...", classes="tab-content")
            with TabPane("Columns", id="tab-columns"):
                yield Static("", classes="tab-content")
            with TabPane("Indexes", id="tab-indexes"):
                yield Static("", classes="tab-content")
            with TabPane("Partitions", id="tab-partitions"):
                yield Static("", classes="tab-content")
            with TabPane("Foreign Keys", id="tab-fk"):
                yield Static("", classes="tab-content")
            with TabPane("Triggers", id="tab-triggers"):
                yield Static("", classes="tab-content")
            with TabPane("Grants", id="tab-grants"):
                yield Static("", classes="tab-content")
            with TabPane("Dependencies", id="tab-deps"):
                yield Static("", classes="tab-content")
            with TabPane("DDL", id="tab-ddl"):
                yield Static("", classes="tab-content")
            with TabPane("Sample Data", id="tab-sample"):
                yield Horizontal(
                    Button("First 5 rows", id="btn-sample-first", variant="primary"),
                    Button("Last 5 rows", id="btn-sample-last", variant="primary"),
                    classes="sample-buttons",
                )
                with VerticalScroll(id="sample-scroll"):
                    yield Static("", id="sample-results", classes="tab-content")


def _format_bytes(size: int) -> str:
    """Format byte size into human-readable string."""
    if size == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    fsize = float(size)
    while fsize >= 1024 and i < len(units) - 1:
        fsize /= 1024
        i += 1
    if i == 0:
        return f"{size} B"
    return f"{fsize:.1f} {units[i]}"
