"""
MySQL connection management.

Wraps mysql-connector-python to provide connection establishment
using Profile settings. Handles SSL modes, compression, timeouts,
login paths, option files, and init commands.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.errors import Error as MySQLError
from mysql.connector.pooling import PooledMySQLConnection

from mydba_tui.models.profile import Profile


class ConnectionResult:
    """Holds the MySQL connection and optional SSH tunnel.

    The tunnel must be kept alive for the duration of the connection.
    Call close() to cleanly shut down both.
    """

    def __init__(
        self,
        connection: MySQLConnectionAbstract | PooledMySQLConnection,
        tunnel: Any = None,
    ) -> None:
        """Initialize connection result.

        Args:
            connection: The MySQL connection.
            tunnel: The SSH tunnel forwarder (if used).
        """
        self.connection = connection
        self.tunnel = tunnel

    def close(self) -> None:
        """Close the connection and stop the tunnel."""
        try:
            self.connection.close()
        except Exception:
            pass
        if self.tunnel is not None:
            try:
                self.tunnel.stop()
            except Exception:
                pass


def connect(profile: Profile, password: str = "") -> ConnectionResult:
    """Establish a MySQL connection using profile settings.

    If the profile has SSH tunnel configuration, establishes the tunnel
    first and connects through it.

    The password parameter is used when the profile has no stored password
    and the user enters it at the prompt.

    Args:
        profile: Connection profile with all settings.
        password: Password provided at runtime (overrides profile.password
            only if profile.password is empty).

    Returns:
        ConnectionResult containing the connection and optional tunnel.

    Raises:
        mysql.connector.errors.Error: If the connection fails.
        Exception: If the SSH tunnel fails to establish.
    """
    from mydba_tui.connection.tunnel import create_tunnel

    tunnel = create_tunnel(profile)
    tunnel_local_port: int | None = None

    if tunnel is not None:
        tunnel.start()
        tunnel_local_port = tunnel.local_port

    kwargs = _build_connect_kwargs(profile, password, tunnel_local_port)

    try:
        connection = mysql.connector.connect(**kwargs)
    except Exception:
        # If connection fails, stop the tunnel
        if tunnel is not None:
            tunnel.stop()
        raise

    # Execute init command if configured
    if profile.init_command:
        cursor = connection.cursor()
        cursor.execute(profile.init_command)
        cursor.close()

    return ConnectionResult(connection, tunnel)


def _build_connect_kwargs(
    profile: Profile, runtime_password: str, tunnel_local_port: int | None = None
) -> dict[str, object]:
    """Build the keyword arguments for mysql.connector.connect().

    Priority:
    1. Explicit profile fields always win.
    2. login_path provides credentials from .mylogin.cnf.
    3. option_file + option_group provide defaults from .my.cnf.

    Args:
        profile: Connection profile.
        runtime_password: Password entered at the prompt.
        tunnel_local_port: Local port from SSH tunnel (overrides host/port).

    Returns:
        Dictionary of connection keyword arguments.
    """
    kwargs: dict[str, object] = {}

    # Option file support (lowest priority — connector reads these first,
    # then explicit kwargs override)
    if profile.option_file:
        option_path = Path(profile.option_file).expanduser()
        if option_path.exists():
            kwargs["option_files"] = str(option_path)
            if profile.option_group:
                kwargs["option_groups"] = ["client", f"client{profile.option_group}"]
    elif not profile.login_path:
        # Fall back to ~/.my.cnf if it exists (same as native mysql client)
        default_mycnf = Path.home() / ".my.cnf"
        if default_mycnf.exists():
            kwargs["option_files"] = str(default_mycnf)
            if profile.option_group:
                kwargs["option_groups"] = ["client", f"client{profile.option_group}"]

    # Login path support (.mylogin.cnf)
    if profile.login_path:
        # mysql-connector-python reads .mylogin.cnf when option_files
        # includes the login path file. We pass it via the dedicated parameter.
        kwargs["option_files"] = kwargs.get("option_files", "")
        kwargs["option_groups"] = [profile.login_path]

    # Explicit connection parameters (override config file values)
    if tunnel_local_port is not None:
        # Tunnel active — connect to local forwarded port
        kwargs["host"] = "127.0.0.1"
        kwargs["port"] = tunnel_local_port
        # Use longer timeout for tunneled connections
        kwargs["connection_timeout"] = max(profile.connect_timeout, 30)
    else:
        kwargs["host"] = profile.host
        kwargs["port"] = profile.port
        kwargs["connection_timeout"] = profile.connect_timeout
    kwargs["autocommit"] = True

    if profile.username:
        kwargs["username"] = profile.username

    # Password priority: runtime prompt > stored in profile > config files
    effective_password = runtime_password or profile.password
    if effective_password:
        kwargs["password"] = effective_password

    if profile.default_database:
        kwargs["database"] = profile.default_database

    # Compression
    if profile.compress:
        kwargs["compress"] = True

    # SSL configuration
    if profile.ssl is not None:
        _apply_ssl_kwargs(kwargs, profile)
    else:
        # Default: let the server decide (PREFERRED behavior)
        kwargs["ssl_disabled"] = False

    return kwargs


def _apply_ssl_kwargs(kwargs: dict[str, object], profile: Profile) -> None:
    """Apply SSL-related connection kwargs based on profile SSL config.

    Args:
        kwargs: Connection kwargs dict to modify in place.
        profile: Profile with SSL configuration.
    """
    ssl = profile.ssl
    if ssl is None:
        return

    mode = ssl.mode.lower()

    if mode == "disabled":
        kwargs["ssl_disabled"] = True
        return

    # All other modes require SSL enabled
    kwargs["ssl_disabled"] = False

    if ssl.ca:
        kwargs["ssl_ca"] = str(Path(ssl.ca).expanduser())
    if ssl.cert:
        kwargs["ssl_cert"] = str(Path(ssl.cert).expanduser())
    if ssl.key:
        kwargs["ssl_key"] = str(Path(ssl.key).expanduser())

    if mode == "verify_ca":
        kwargs["ssl_verify_cert"] = True
    elif mode == "verify_identity":
        kwargs["ssl_verify_cert"] = True
        kwargs["ssl_verify_identity"] = True


class ConnectionError(Exception):
    """Wrapper for MySQL connection errors with a user-friendly message."""

    def __init__(self, message: str, mysql_error: MySQLError | None = None) -> None:
        """Initialize connection error.

        Args:
            message: Human-readable error description.
            mysql_error: The original MySQL error, if any.
        """
        super().__init__(message)
        self.mysql_error = mysql_error
