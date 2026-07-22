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
        width: 32;
        min-width: 20;
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
            content.update(
                f"[b]{schema}.{name}[/b] ({category[:-1]})\n\n"
                f"[dim]Metadata view will be added in the next step.[/dim]"
            )

    def action_open_profiles(self) -> None:
        """Navigate to Connection Profiles."""
        self.app.push_screen("profiles")

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()
