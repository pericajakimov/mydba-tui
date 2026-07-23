"""
Main workspace screen.

The primary interface after connecting to a database.
Split-pane layout: object browser tree on the left,
content/working area on the right.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Tree
from textual.widgets.tree import TreeNode

from mydba_tui.ui.widgets import StatusBar


class MainWorkspaceScreen(Screen[None]):
    """Main workspace with split-pane layout."""

    BINDINGS = [
        Binding("c", "open_profiles", "Connections", key_display="C"),
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
        padding: 1 2;
        overflow-y: auto;
    }

    #content-placeholder {
        color: $text-muted;
    }
    """

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
                    id="content-placeholder",
                )

        yield Footer()

    def on_mount(self) -> None:
        """Load schemas into the tree on mount."""
        self._sync_status_bar()
        self._load_schemas()

    def on_screen_resume(self) -> None:
        """Update status bar and reload schemas when returning to this screen."""
        self._sync_status_bar()
        self._load_schemas()

    def _sync_status_bar(self) -> None:
        """Sync status bar with current connection state."""
        status = getattr(self.app, "connection_status", "")
        if status:
            self.query_one("#status-bar", StatusBar).status_text = status

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

        # Mark as loaded so we don't re-query
        data["loaded"] = True

        # Add object type categories (expandable to list objects)
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

        content = self.query_one("#content-placeholder", Static)

        if data.get("type") == "schema":
            schema_name = data["name"]
            content.update(f"[b]{schema_name}[/b]\n\n[dim]Expand to browse objects.[/dim]")
        elif data.get("type") == "category":
            schema = data["schema"]
            category = data["category"]
            content.update(
                f"[b]{schema}[/b] — {category.capitalize()}\n\n[dim]Expand to list objects.[/dim]"
            )
        elif data.get("type") == "object":
            schema = data["schema"]
            category = data["category"]
            name = data["name"]
            if category == "tables":
                self._show_table_metadata(schema, name)
            else:
                content.update(
                    f"[b]{schema}.{name}[/b] ({category[:-1]})\n\n"
                    f"[dim]Metadata view for {category} coming soon.[/dim]"
                )

    def _show_table_metadata(self, schema: str, table: str) -> None:
        """Show table metadata in the content panel."""
        from mydba_tui.connection import ConnectionResult
        from mydba_tui.services.browser import (
            get_table_columns,
            get_table_indexes,
            get_table_info,
        )

        conn_result = getattr(self.app, "db_connection", None)
        if conn_result is None or not isinstance(conn_result, ConnectionResult):
            return

        content = self.query_one("#content-placeholder", Static)

        try:
            info = get_table_info(conn_result.connection, schema, table)
            columns = get_table_columns(conn_result.connection, schema, table)
            indexes = get_table_indexes(conn_result.connection, schema, table)
        except Exception as e:
            content.update(f"[red]Error loading metadata: {e}[/red]")
            return
        # Calculate fragmentation
        total_size = info.data_size + info.index_size
        frag_pct = f"{(info.data_free / total_size * 100):.1f}%" if total_size > 0 else "0%"

        # Format general info — right-aligned labels
        lines: list[str] = []
        lines.append(f"[bold cyan]{schema}.{table}[/bold cyan] [dim](table)[/dim]\n")
        lines.append("[bold yellow]General[/bold yellow]")
        lines.append(f"        [dim]Engine:[/dim] {info.engine}")
        lines.append(f"    [dim]Row Format:[/dim] {info.row_format}")
        lines.append(f"  [dim]Rows (approx):[/dim] {info.row_count:,}")
        lines.append(f"[dim]Avg Row Length:[/dim] {info.avg_row_length:,} bytes")
        lines.append(f"     [dim]Data Size:[/dim] {_format_bytes(info.data_size)}")
        lines.append(f"    [dim]Index Size:[/dim] {_format_bytes(info.index_size)}")
        lines.append(f"    [dim]Total Size:[/dim] {_format_bytes(total_size)}")
        lines.append(f"    [dim]Free Space:[/dim] {_format_bytes(info.data_free)}")
        lines.append(f" [dim]Fragmentation:[/dim] {frag_pct}")
        lines.append(
            f"[dim]Auto Increment:[/dim] {info.auto_increment:,}"
            if info.auto_increment is not None
            else "[dim]Auto Increment:[/dim]"
        )
        lines.append(f"     [dim]Collation:[/dim] {info.collation}")
        if info.create_options:
            lines.append(f"       [dim]Options:[/dim] {info.create_options}")
        lines.append(f"       [dim]Created:[/dim] {info.create_time}")
        lines.append(f"       [dim]Updated:[/dim] {info.update_time or ''}")
        lines.append(f"       [dim]Checked:[/dim] {info.check_time or ''}")
        lines.append(f"       [dim]Comment:[/dim] {info.comment or ''}")

        # Format columns
        lines.append("")
        lines.append(f"[bold yellow]Columns ({len(columns)})[/bold yellow]")
        if columns:
            lines.append(
                f"  [bold]{'#':<3} {'Name':<30} {'Type':<20} "
                f"{'Null':<5} {'Key':<4} {'Extra'}[/bold]"
            )
            lines.append(f"  {'─' * 3} {'─' * 30} {'─' * 20} {'─' * 5} {'─' * 4} {'─' * 15}")
            for col in columns:
                nullable = "YES" if col.nullable == "YES" else "NO"
                key_display = (
                    f"[bold green]{col.key}[/bold green]"
                    if col.key == "PRI"
                    else f"[cyan]{col.key}[/cyan]"
                    if col.key
                    else ""
                )
                lines.append(
                    f"  {col.position:<3} {col.name:<30} "
                    f"[dim]{col.col_type:<20}[/dim] "
                    f"{nullable:<5} {key_display:<4} {col.extra}"
                )

        # Format indexes
        lines.append("")
        lines.append("[bold yellow]Indexes[/bold yellow]")
        if indexes:
            # Group by index name, show columns with cardinality and selectivity
            seen: set[str] = set()
            for idx in indexes:
                if idx.name in seen:
                    continue
                seen.add(idx.name)

                # Collect all columns for this index
                idx_entries = [i for i in indexes if i.name == idx.name]
                cols_parts = []
                for entry in idx_entries:
                    col_display = entry.expression if entry.expression else entry.column
                    cols_parts.append(col_display)
                cols_str = ", ".join(cols_parts)

                # Build index header
                if idx.name == "PRIMARY":
                    prefix = "[bold green]PRIMARY[/bold green]"
                elif idx.non_unique == 0:
                    prefix = f"[green]UNIQUE[/green] {idx.name}"
                else:
                    prefix = idx.name

                # Visibility flag
                vis_flag = " [dim]— INVISIBLE[/dim]" if idx.visible == "NO" else ""

                lines.append(f"  {prefix} [dim]({idx.index_type}){vis_flag}[/dim]")
                lines.append(f"    Columns: [cyan]{cols_str}[/cyan]")

                # Cardinality (use the last entry's cardinality — full index cardinality)
                last_entry = idx_entries[-1]
                if last_entry.cardinality > 0:
                    card_str = f"{last_entry.cardinality:,}"
                    # Selectivity
                    if info.row_count > 0:
                        selectivity = last_entry.cardinality / info.row_count * 100
                        sel_str = f"{selectivity:.1f}%"
                        if selectivity < 1.0 and idx.name != "PRIMARY":
                            card_str += (
                                f" [dim](selectivity: {sel_str})[/dim] [yellow]⚠ low[/yellow]"
                            )
                        else:
                            card_str += f" [dim](selectivity: {sel_str})[/dim]"
                    lines.append(f"    Cardinality: {card_str}")

                # Comment if present
                if idx.comment:
                    lines.append(f"    Comment: {idx.comment}")

                lines.append("")
        else:
            lines.append("  [dim]No indexes[/dim]")

        content.update("\n".join(lines))

    def action_open_profiles(self) -> None:
        """Navigate to Connection Profiles."""
        self.app.push_screen("profiles")

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()


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
