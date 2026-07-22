"""
Profile add/edit form screen.

A modal form for creating or editing a connection profile.
Returns the Profile on dismiss, or None if cancelled.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Collapsible, Input, Label, Select, Static, Switch

from mydba_tui.models.profile import Profile, SshTunnelConfig, SslConfig


class ProfileFormScreen(ModalScreen[Profile | None]):
    """Form for creating or editing a connection profile."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    ProfileFormScreen {
        align: center middle;
    }

    #form-container {
        width: 70;
        height: auto;
        max-height: 85%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
        overflow-y: auto;
    }

    #form-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
    }

    .form-row {
        layout: horizontal;
        height: auto;
    }

    .form-field {
        width: 1fr;
        height: auto;
        padding: 0 1 0 0;
    }

    .form-field-last {
        width: 1fr;
        height: auto;
    }

    .form-label {
        margin-top: 1;
    }

    .form-input {
        margin-bottom: 0;
    }

    #button-row {
        margin-top: 1;
        align: center middle;
        height: auto;
        layout: horizontal;
    }

    #button-row Button {
        margin: 0 1;
    }

    .section-note {
        color: $text-muted;
        margin-bottom: 1;
    }
    """

    def __init__(self, profile: Profile | None = None) -> None:
        """Initialize the form.

        Args:
            profile: Existing profile to edit, or None for a new profile.
        """
        super().__init__()
        self._profile = profile

    def compose(self) -> ComposeResult:
        """Build the form layout."""
        title = "Edit Profile" if self._profile is not None else "New Profile"
        p = self._profile or Profile()

        with Vertical(id="form-container"):
            yield Static(title, id="form-title")

            yield Label("Name:", classes="form-label")
            yield Input(
                value=p.name,
                placeholder="e.g. Payments_perica",
                id="input-name",
                classes="form-input",
            )

            yield Label("Host:", classes="form-label")
            yield Input(
                value=p.host,
                placeholder="e.g. payments-writer.cluster-abc123.us-east-1.rds.amazonaws.com",
                id="input-host",
                classes="form-input",
            )

            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Environment:", classes="form-label")
                    yield Select(
                        options=[
                            ("PROD", "prod"),
                            ("STAGE", "stage"),
                            ("QA", "qa"),
                            ("DEV", "dev"),
                        ],
                        value=p.environment,
                        id="input-environment",
                    )
                with Vertical(classes="form-field-last"):
                    yield Label("Port:", classes="form-label")
                    yield Input(
                        value=str(p.port),
                        placeholder="3306",
                        id="input-port",
                        classes="form-input",
                    )

            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Username:", classes="form-label")
                    yield Input(
                        value=p.username,
                        placeholder="(optional)",
                        id="input-username",
                        classes="form-input",
                    )
                with Vertical(classes="form-field-last"):
                    yield Label("Default Database:", classes="form-label")
                    yield Input(
                        value=p.default_database,
                        placeholder="(optional)",
                        id="input-database",
                        classes="form-input",
                    )

            # Advanced — password, timeout, compress, init_command
            with Collapsible(
                title="Advanced",
                collapsed=not self._has_advanced_values(p),
            ):
                yield Static(
                    "[dim]Password storage is discouraged on shared systems.[/dim]",
                    classes="section-note",
                )
                with Horizontal(classes="form-row"):
                    with Vertical(classes="form-field"):
                        yield Label("MySQL Password:", classes="form-label")
                        yield Input(
                            value=p.password,
                            placeholder="(leave empty to prompt on connect)",
                            password=True,
                            id="input-password",
                            classes="form-input",
                        )
                    with Vertical(classes="form-field-last"):
                        yield Label("Save:", classes="form-label")
                        yield Switch(
                            value=p.store_password,
                            id="input-store-password",
                        )

                with Horizontal(classes="form-row"):
                    with Vertical(classes="form-field"):
                        yield Label("Connect Timeout (sec):", classes="form-label")
                        yield Input(
                            value=str(p.connect_timeout),
                            placeholder="10",
                            id="input-timeout",
                            classes="form-input",
                        )
                    with Vertical(classes="form-field-last"):
                        yield Label("Compress:", classes="form-label")
                        yield Switch(
                            value=p.compress,
                            id="input-compress",
                        )

                yield Label("Init Command:", classes="form-label")
                yield Input(
                    value=p.init_command,
                    placeholder="e.g. SET SESSION wait_timeout=28800",
                    id="input-init-command",
                    classes="form-input",
                )

            # SSL options
            with Collapsible(
                title="SSL options",
                collapsed=not self._has_ssl_values(p),
            ):
                with Horizontal(classes="form-row"):
                    with Vertical(classes="form-field"):
                        yield Label("SSL Mode:", classes="form-label")
                        yield Select(
                            options=[
                                ("DISABLED", "disabled"),
                                ("PREFERRED", "preferred"),
                                ("REQUIRED", "required"),
                                ("VERIFY_CA", "verify_ca"),
                                ("VERIFY_IDENTITY", "verify_identity"),
                            ],
                            value=p.ssl.mode if p.ssl else "preferred",
                            id="input-ssl-mode",
                        )
                    with Vertical(classes="form-field-last"):
                        yield Label("CA Certificate:", classes="form-label")
                        yield Input(
                            value=p.ssl.ca if p.ssl else "",
                            placeholder="/path/to/ca.pem",
                            id="input-ssl-ca",
                            classes="form-input",
                        )

                with Horizontal(classes="form-row"):
                    with Vertical(classes="form-field"):
                        yield Label("Client Cert:", classes="form-label")
                        yield Input(
                            value=p.ssl.cert if p.ssl else "",
                            placeholder="/path/to/client-cert.pem",
                            id="input-ssl-cert",
                            classes="form-input",
                        )
                    with Vertical(classes="form-field-last"):
                        yield Label("Client Key:", classes="form-label")
                        yield Input(
                            value=p.ssl.key if p.ssl else "",
                            placeholder="/path/to/client-key.pem",
                            id="input-ssl-key",
                            classes="form-input",
                        )

            # SSH jumphost
            with Collapsible(
                title="SSH jumphost",
                collapsed=not self._has_ssh_values(p),
            ):
                with Horizontal(classes="form-row"):
                    with Vertical(classes="form-field"):
                        yield Label("Host:", classes="form-label")
                        yield Input(
                            value=p.ssh_tunnel.host if p.ssh_tunnel else "",
                            placeholder="jump.example.com",
                            id="input-ssh-host",
                            classes="form-input",
                        )
                    with Vertical(classes="form-field-last"):
                        yield Label("Port:", classes="form-label")
                        yield Input(
                            value=str(p.ssh_tunnel.port) if p.ssh_tunnel else "22",
                            placeholder="22",
                            id="input-ssh-port",
                            classes="form-input",
                        )

                with Horizontal(classes="form-row"):
                    with Vertical(classes="form-field"):
                        yield Label("Username:", classes="form-label")
                        yield Input(
                            value=p.ssh_tunnel.username if p.ssh_tunnel else "",
                            placeholder="(optional)",
                            id="input-ssh-username",
                            classes="form-input",
                        )
                    with Vertical(classes="form-field-last"):
                        yield Label("Key File:", classes="form-label")
                        yield Input(
                            value=p.ssh_tunnel.key_file if p.ssh_tunnel else "",
                            placeholder="~/.ssh/id_rsa",
                            id="input-ssh-key",
                            classes="form-input",
                        )

                with Horizontal(classes="form-row"):
                    with Vertical(classes="form-field"):
                        yield Label("SSH Password:", classes="form-label")
                        yield Input(
                            value=p.ssh_tunnel.password if p.ssh_tunnel else "",
                            placeholder="(leave empty to prompt or use key)",
                            password=True,
                            id="input-ssh-password",
                            classes="form-input",
                        )
                    with Vertical(classes="form-field-last"):
                        yield Label("Save:", classes="form-label")
                        yield Switch(
                            value=p.ssh_tunnel.store_password if p.ssh_tunnel else False,
                            id="input-ssh-store-password",
                        )

            with Horizontal(id="button-row"):
                yield Button("Save", variant="primary", id="btn-save")
                yield Button("Cancel", id="btn-cancel")

    @staticmethod
    def _has_advanced_values(profile: Profile) -> bool:
        """Check if the profile has any advanced fields set."""
        if profile.store_password or profile.password:
            return True
        if profile.connect_timeout != 10:
            return True
        if profile.compress:
            return True
        if profile.init_command:
            return True
        return False

    @staticmethod
    def _has_ssl_values(profile: Profile) -> bool:
        """Check if the profile has SSL configuration."""
        if profile.ssl is None:
            return False
        return bool(profile.ssl.ca or profile.ssl.mode != "preferred")

    @staticmethod
    def _has_ssh_values(profile: Profile) -> bool:
        """Check if the profile has SSH tunnel configuration."""
        if profile.ssh_tunnel is None:
            return False
        return bool(profile.ssh_tunnel.host)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-save":
            self._save()
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

    def _save(self) -> None:
        """Validate and return the profile."""
        name = self.query_one("#input-name", Input).value.strip()
        if not name:
            self.notify("Name is required.", severity="error")
            return

        host = self.query_one("#input-host", Input).value.strip()
        if not host:
            self.notify("Host is required.", severity="error")
            return

        port_str = self.query_one("#input-port", Input).value.strip()
        try:
            port = int(port_str) if port_str else 3306
        except ValueError:
            self.notify("Port must be a number.", severity="error")
            return

        environment_select = self.query_one("#input-environment", Select)
        environment = str(environment_select.value) if environment_select.value else "dev"

        username = self.query_one("#input-username", Input).value.strip()
        database = self.query_one("#input-database", Input).value.strip()

        # Advanced
        store_password = self.query_one("#input-store-password", Switch).value
        password = self.query_one("#input-password", Input).value.strip()

        timeout_str = self.query_one("#input-timeout", Input).value.strip()
        try:
            connect_timeout = int(timeout_str) if timeout_str else 10
        except ValueError:
            connect_timeout = 10

        compress = self.query_one("#input-compress", Switch).value
        init_command = self.query_one("#input-init-command", Input).value.strip()

        # SSL
        ssl_mode_select = self.query_one("#input-ssl-mode", Select)
        ssl_mode = str(ssl_mode_select.value) if ssl_mode_select.value else "preferred"
        ssl_ca = self.query_one("#input-ssl-ca", Input).value.strip()
        ssl_cert = self.query_one("#input-ssl-cert", Input).value.strip()
        ssl_key = self.query_one("#input-ssl-key", Input).value.strip()
        ssl: SslConfig | None = None
        if ssl_mode != "preferred" or ssl_ca or ssl_cert or ssl_key:
            ssl = SslConfig(mode=ssl_mode, ca=ssl_ca, cert=ssl_cert, key=ssl_key)

        # SSH
        ssh_host = self.query_one("#input-ssh-host", Input).value.strip()
        ssh_username = self.query_one("#input-ssh-username", Input).value.strip()
        ssh_port_str = self.query_one("#input-ssh-port", Input).value.strip()
        ssh_key_file = self.query_one("#input-ssh-key", Input).value.strip()
        ssh_store_password = self.query_one("#input-ssh-store-password", Switch).value
        ssh_password = self.query_one("#input-ssh-password", Input).value.strip()
        ssh_tunnel: SshTunnelConfig | None = None
        if ssh_host:
            try:
                ssh_port = int(ssh_port_str) if ssh_port_str else 22
            except ValueError:
                ssh_port = 22
            ssh_tunnel = SshTunnelConfig(
                host=ssh_host,
                port=ssh_port,
                username=ssh_username,
                key_file=ssh_key_file,
                store_password=ssh_store_password,
                password=ssh_password if ssh_store_password else "",
            )

        profile = Profile(
            name=name,
            environment=environment,
            host=host,
            port=port,
            username=username,
            default_database=database,
            connect_timeout=connect_timeout,
            compress=compress,
            init_command=init_command,
            ssl=ssl,
            ssh_tunnel=ssh_tunnel,
            store_password=store_password,
            password=password if store_password else "",
        )

        self.dismiss(profile)

    def action_cancel(self) -> None:
        """Cancel the form."""
        self.dismiss(None)
