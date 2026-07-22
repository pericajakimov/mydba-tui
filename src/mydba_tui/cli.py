"""
Command-line argument parsing.

Supports standard MySQL client connection flags for familiarity.
When connection parameters are provided, the app connects directly
instead of showing the profile selection screen.
"""

import argparse
import sys
from dataclasses import dataclass

from mydba_tui import __version__
from mydba_tui.models.profile import Profile, SslConfig


@dataclass(slots=True)
class CliOptions:
    """Parsed command-line options.

    Attributes:
        profile_name: Named profile to use (--profile).
        connect_directly: True if connection params were provided on CLI.
        cli_profile: Profile built from CLI flags (if connect_directly).
        password_prompt: True if -p was given without a value.
    """

    profile_name: str = ""
    connect_directly: bool = False
    cli_profile: Profile | None = None
    password_prompt: bool = False


def parse_args(argv: list[str] | None = None) -> CliOptions:
    """Parse command-line arguments.

    Supports mysql-compatible connection flags.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed CLI options.
    """
    # Handle mysql-style -pPASSWORD (no space) before argparse sees it
    if argv is None:
        argv = sys.argv[1:]
    argv, inline_password = _extract_inline_password(argv)

    parser = argparse.ArgumentParser(
        prog="mydba",
        description="A keyboard-first terminal MySQL DBA productivity tool.",
        add_help=False,
    )

    # Help (can't use -h since it's for --host)
    parser.add_argument(
        "--help", action="help", default=argparse.SUPPRESS, help="Show this help message and exit"
    )

    # Connection options (matching mysql client)
    conn = parser.add_argument_group("connection options")
    conn.add_argument("-h", "--host", metavar="HOST", help="Server hostname (default: 127.0.0.1)")
    conn.add_argument("-P", "--port", type=int, metavar="PORT", help="Server port (default: 3306)")
    conn.add_argument("-u", "--user", metavar="USER", help="MySQL username")
    conn.add_argument(
        "-p",
        "--password",
        nargs="?",
        const=True,
        default=None,
        metavar="PASSWORD",
        help="Password (prompted if flag given without value)",
    )
    conn.add_argument("-D", "--database", metavar="DB", help="Default database")
    conn.add_argument("-C", "--compress", action="store_true", help="Enable protocol compression")
    conn.add_argument(
        "--connect-timeout",
        type=int,
        metavar="SEC",
        help="Connection timeout in seconds (default: 10)",
    )

    # Config file options
    cfg = parser.add_argument_group("config file options")
    cfg.add_argument("--login-path", metavar="NAME", help="Login path from .mylogin.cnf")
    cfg.add_argument(
        "--defaults-file", metavar="FILE", help="Option file path (instead of ~/.my.cnf)"
    )
    cfg.add_argument(
        "--defaults-group-suffix",
        metavar="SUFFIX",
        help="Option group suffix (e.g. _payments)",
    )

    # SSL options
    ssl_group = parser.add_argument_group("SSL options")
    ssl_group.add_argument(
        "--ssl-mode",
        choices=["DISABLED", "PREFERRED", "REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"],
        metavar="MODE",
        help="SSL mode (DISABLED, PREFERRED, REQUIRED, VERIFY_CA, VERIFY_IDENTITY)",
    )
    ssl_group.add_argument("--ssl-ca", metavar="FILE", help="CA certificate path")
    ssl_group.add_argument("--ssl-cert", metavar="FILE", help="Client certificate path")
    ssl_group.add_argument("--ssl-key", metavar="FILE", help="Client key path")

    # mydba-specific options
    mydba = parser.add_argument_group("mydba options")
    mydba.add_argument("--profile", metavar="NAME", help="Connect using a saved profile")
    mydba.add_argument("--init-command", metavar="SQL", help="SQL to execute after connecting")
    mydba.add_argument("-V", "--version", action="version", version=f"mydba {__version__}")

    args = parser.parse_args(argv)

    options = CliOptions()

    # Named profile mode
    if args.profile:
        options.profile_name = args.profile
        options.connect_directly = True
        return options

    # Direct connection mode — build a Profile from CLI flags
    has_connection_args = any(
        [
            args.host,
            args.port,
            args.user,
            args.password is not None,
            args.database,
            args.login_path,
            args.defaults_file,
        ]
    )

    if has_connection_args:
        ssl = _build_ssl_config(args)
        profile = Profile(
            name="cli",
            host=args.host or "127.0.0.1",
            port=args.port or 3306,
            username=args.user or "",
            default_database=args.database or "",
            connect_timeout=args.connect_timeout or 10,
            compress=args.compress,
            init_command=args.init_command or "",
            login_path=args.login_path or "",
            option_file=args.defaults_file or "",
            option_group=args.defaults_group_suffix or "",
            ssl=ssl,
            password=inline_password or "",
        )

        options.connect_directly = True
        options.cli_profile = profile

        # -p with no value means prompt for password
        if args.password is True:
            options.password_prompt = True
        elif isinstance(args.password, str):
            profile.password = args.password

    return options


def _extract_inline_password(argv: list[str]) -> tuple[list[str], str]:
    """Extract mysql-style -pPASSWORD (no space between -p and value).

    Args:
        argv: Raw argument list.

    Returns:
        Tuple of (cleaned argv, extracted password or empty string).
    """
    cleaned = []
    password = ""
    for arg in argv:
        if (
            arg.startswith("-p")
            and arg != "-p"
            and arg != "--password"
            and not arg.startswith("--")
        ):
            # -pSECRET style
            password = arg[2:]
        else:
            cleaned.append(arg)
    return cleaned, password


def _build_ssl_config(args: argparse.Namespace) -> SslConfig | None:
    """Build SslConfig from CLI arguments.

    Args:
        args: Parsed argparse namespace.

    Returns:
        SslConfig if any SSL options were provided, else None.
    """
    has_ssl = any([args.ssl_mode, args.ssl_ca, args.ssl_cert, args.ssl_key])
    if not has_ssl:
        return None

    return SslConfig(
        mode=(args.ssl_mode or "preferred").lower(),
        ca=args.ssl_ca or "",
        cert=args.ssl_cert or "",
        key=args.ssl_key or "",
    )
