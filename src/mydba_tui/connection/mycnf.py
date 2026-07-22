"""
MySQL configuration file reader.

Parses .my.cnf files to determine which credentials are already
available, so the application only prompts for missing information.
"""

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class MyCnfCredentials:
    """Credentials found in a .my.cnf file.

    Empty string means the field was not found in the config.
    """

    user: str = ""
    password: str = ""
    host: str = ""
    port: str = ""


def read_mycnf_credentials(
    option_file: str = "",
    option_group: str = "",
) -> MyCnfCredentials:
    """Read credentials from a .my.cnf file.

    Reads the [client] section (and optionally [client<suffix>] if
    option_group is provided). The suffix group overrides base values.

    Args:
        option_file: Path to the .my.cnf file. Defaults to ~/.my.cnf.
        option_group: Group suffix (e.g. "_payments" reads [client_payments]).

    Returns:
        Credentials found in the config file.
    """
    if option_file:
        path = Path(option_file).expanduser()
    else:
        path = Path.home() / ".my.cnf"

    if not path.exists():
        return MyCnfCredentials()

    config = configparser.ConfigParser(interpolation=None)
    config.read(str(path), encoding="utf-8")

    creds = MyCnfCredentials()

    # Read [client] section first
    if config.has_section("client"):
        creds.user = config.get("client", "user", fallback="")
        creds.password = config.get("client", "password", fallback="")
        creds.host = config.get("client", "host", fallback="")
        creds.port = config.get("client", "port", fallback="")

    # Override with [client<suffix>] if specified
    if option_group:
        suffix_section = f"client{option_group}"
        if config.has_section(suffix_section):
            user = config.get(suffix_section, "user", fallback="")
            if user:
                creds.user = user
            password = config.get(suffix_section, "password", fallback="")
            if password:
                creds.password = password
            host = config.get(suffix_section, "host", fallback="")
            if host:
                creds.host = host
            port = config.get(suffix_section, "port", fallback="")
            if port:
                creds.port = port

    return creds
