"""
Connection profile data model.

Represents a single database endpoint that the user can connect to.
Each profile maps to exactly one MySQL-compatible server.
"""

from dataclasses import asdict, dataclass
from enum import Enum

from mydba_tui.utils.obfuscate import deobfuscate, obfuscate


class Environment(Enum):
    """Supported deployment environments.

    The environment determines visual identification (color) in the UI
    and is used for grouping profiles.
    """

    PROD = "prod"
    STAGE = "stage"
    QA = "qa"
    DEV = "dev"


class SslMode(Enum):
    """MySQL SSL connection modes.

    Maps to mysql --ssl-mode values:
    - DISABLED: No SSL.
    - PREFERRED: Use SSL if server supports it, fall back to unencrypted.
    - REQUIRED: Require SSL, do not verify server certificate.
    - VERIFY_CA: Require SSL and verify server CA certificate.
    - VERIFY_IDENTITY: Require SSL, verify CA, and verify server hostname.
    """

    DISABLED = "disabled"
    PREFERRED = "preferred"
    REQUIRED = "required"
    VERIFY_CA = "verify_ca"
    VERIFY_IDENTITY = "verify_identity"


@dataclass(slots=True)
class SslConfig:
    """SSL connection configuration.

    Attributes:
        mode: SSL mode (disabled, preferred, required, verify_ca, verify_identity).
        ca: Path to the CA certificate file.
        cert: Path to the client certificate file.
        key: Path to the client key file.
    """

    mode: str = "preferred"
    ca: str = ""
    cert: str = ""
    key: str = ""


@dataclass(slots=True)
class SshTunnelConfig:
    """SSH tunnel configuration for connecting through a jump host.

    Attributes:
        host: SSH server hostname.
        port: SSH server port.
        username: SSH username.
        key_file: Path to the SSH private key file.
        password: SSH password (empty means prompt or use key).
    """

    host: str = ""
    port: int = 22
    username: str = ""
    key_file: str = ""
    password: str = ""


@dataclass(slots=True)
class Profile:
    """Connection profile representing a single database endpoint.

    Attributes:
        name: Unique connection name (primary identifier shown to user).
        environment: Deployment environment (prod, stage, qa, dev).
        host: Database server hostname or IP.
        port: Database server port.
        username: MySQL username (optional, prompted if empty).
        default_database: Default database to use after connection.
        connect_timeout: Connection timeout in seconds (default: 10).
        compress: Whether to use compressed protocol.
        init_command: SQL to execute immediately after connecting.
        login_path: Login path name from .mylogin.cnf (like --login-path).
        option_file: Path to a .my.cnf file (like --defaults-file).
        option_group: Group suffix for .my.cnf (like --defaults-group-suffix).
        ssl: SSL configuration (optional).
        ssh_tunnel: SSH tunnel configuration (optional).
        password: MySQL password (empty means prompt on connect).
    """

    name: str = ""
    environment: str = "dev"
    host: str = "127.0.0.1"
    port: int = 3306
    username: str = ""
    default_database: str = ""
    connect_timeout: int = 10
    compress: bool = False
    init_command: str = ""
    login_path: str = ""
    option_file: str = ""
    option_group: str = ""
    ssl: SslConfig | None = None
    ssh_tunnel: SshTunnelConfig | None = None
    password: str = ""

    def to_dict(self) -> dict[str, object]:
        """Convert profile to a dictionary for YAML serialization.

        Excludes None values and empty nested configs to keep
        the profiles.yaml file clean and readable.

        Returns:
            Dictionary representation of the profile.
        """
        data: dict[str, object] = {
            "name": self.name,
            "environment": self.environment,
            "host": self.host,
            "port": self.port,
        }

        if self.username:
            data["username"] = self.username
        if self.default_database:
            data["default_database"] = self.default_database
        if self.connect_timeout != 10:
            data["connect_timeout"] = self.connect_timeout
        if self.compress:
            data["compress"] = True
        if self.init_command:
            data["init_command"] = self.init_command
        if self.login_path:
            data["login_path"] = self.login_path
        if self.option_file:
            data["option_file"] = self.option_file
        if self.option_group:
            data["option_group"] = self.option_group
        if self.ssl is not None:
            data["ssl"] = asdict(self.ssl)
        if self.ssh_tunnel is not None:
            ssh_data = asdict(self.ssh_tunnel)
            if self.ssh_tunnel.password:
                ssh_data["password"] = obfuscate(self.ssh_tunnel.password)
            else:
                ssh_data.pop("password", None)
            data["ssh_tunnel"] = ssh_data
        if self.password:
            data["password"] = obfuscate(self.password)

        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Profile":
        """Create a Profile from a dictionary (loaded from YAML).

        Args:
            data: Dictionary with profile fields.

        Returns:
            Profile instance.
        """
        ssl_data = data.get("ssl")
        if isinstance(ssl_data, dict):
            ssl_fields = {k: v for k, v in ssl_data.items() if hasattr(SslConfig, k)}
            ssl = SslConfig(**ssl_fields)
        else:
            ssl = None

        ssh_data = data.get("ssh_tunnel")
        if isinstance(ssh_data, dict):
            ssh_fields = {k: v for k, v in ssh_data.items() if hasattr(SshTunnelConfig, k)}
            if "password" in ssh_fields:
                ssh_fields["password"] = deobfuscate(str(ssh_fields["password"]))
            ssh_tunnel = SshTunnelConfig(**ssh_fields)
        else:
            ssh_tunnel = None

        port_value = data.get("port", 3306)
        port = int(port_value) if isinstance(port_value, (int, str)) else 3306

        timeout_value = data.get("connect_timeout", 10)
        connect_timeout = int(timeout_value) if isinstance(timeout_value, (int, str)) else 10

        return cls(
            name=str(data.get("name", "")),
            environment=str(data.get("environment", "dev")),
            host=str(data.get("host", "127.0.0.1")),
            port=port,
            username=str(data.get("username", "")),
            default_database=str(data.get("default_database", "")),
            connect_timeout=connect_timeout,
            compress=bool(data.get("compress", False)),
            init_command=str(data.get("init_command", "")),
            login_path=str(data.get("login_path", "")),
            option_file=str(data.get("option_file", "")),
            option_group=str(data.get("option_group", "")),
            ssl=ssl,
            ssh_tunnel=ssh_tunnel,
            password=deobfuscate(str(data.get("password", ""))),
        )
