"""
MySQL connection management.

Wraps mysql-connector-python to provide connection establishment
using Profile settings. Handles SSL modes, compression, timeouts,
login paths, option files, and init commands.
"""

from pathlib import Path

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.errors import Error as MySQLError
from mysql.connector.pooling import PooledMySQLConnection

from mydba_tui.models.profile import Profile


def connect(
    profile: Profile, password: str = ""
) -> MySQLConnectionAbstract | PooledMySQLConnection:
    """Establish a MySQL connection using profile settings.

    The password parameter is used when the profile has no stored password
    and the user enters it at the prompt.

    Args:
        profile: Connection profile with all settings.
        password: Password provided at runtime (overrides profile.password
            only if profile.password is empty).

    Returns:
        An established MySQL connection.

    Raises:
        mysql.connector.errors.Error: If the connection fails.
    """
    kwargs = _build_connect_kwargs(profile, password)
    connection = mysql.connector.connect(**kwargs)

    # Execute init command if configured
    if profile.init_command:
        cursor = connection.cursor()
        cursor.execute(profile.init_command)
        cursor.close()

    return connection


def _build_connect_kwargs(profile: Profile, runtime_password: str) -> dict[str, object]:
    """Build the keyword arguments for mysql.connector.connect().

    Priority:
    1. Explicit profile fields always win.
    2. login_path provides credentials from .mylogin.cnf.
    3. option_file + option_group provide defaults from .my.cnf.

    Args:
        profile: Connection profile.
        runtime_password: Password entered at the prompt.

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
