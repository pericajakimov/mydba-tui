"""Tests for CLI argument parsing."""

from mydba_tui.cli import parse_args


def test_no_args_returns_defaults() -> None:
    """No arguments should return non-connect mode."""
    options = parse_args([])
    assert options.connect_directly is False
    assert options.cli_profile is None
    assert options.profile_name == ""


def test_host_flag() -> None:
    """Should parse -h HOST."""
    options = parse_args(["-h", "db.example.com"])
    assert options.connect_directly is True
    assert options.cli_profile is not None
    assert options.cli_profile.host == "db.example.com"


def test_port_flag() -> None:
    """Should parse -P PORT."""
    options = parse_args(["-h", "db", "-P", "3307"])
    assert options.cli_profile is not None
    assert options.cli_profile.port == 3307


def test_user_flag() -> None:
    """Should parse -u USER."""
    options = parse_args(["-h", "db", "-u", "admin"])
    assert options.cli_profile is not None
    assert options.cli_profile.username == "admin"


def test_password_prompt_flag() -> None:
    """Should set password_prompt when -p given without value."""
    options = parse_args(["-h", "db", "-u", "admin", "-p"])
    assert options.password_prompt is True
    assert options.cli_profile is not None
    assert options.cli_profile.password == ""


def test_inline_password() -> None:
    """Should extract -pSECRET (no space) style password."""
    options = parse_args(["-h", "db", "-u", "admin", "-pMySecret"])
    assert options.cli_profile is not None
    assert options.cli_profile.password == "MySecret"
    assert options.password_prompt is False


def test_database_flag() -> None:
    """Should parse -D DATABASE."""
    options = parse_args(["-h", "db", "-D", "payments"])
    assert options.cli_profile is not None
    assert options.cli_profile.default_database == "payments"


def test_compress_flag() -> None:
    """Should parse -C / --compress."""
    options = parse_args(["-h", "db", "-C"])
    assert options.cli_profile is not None
    assert options.cli_profile.compress is True


def test_connect_timeout_flag() -> None:
    """Should parse --connect-timeout."""
    options = parse_args(["-h", "db", "--connect-timeout", "30"])
    assert options.cli_profile is not None
    assert options.cli_profile.connect_timeout == 30


def test_login_path_flag() -> None:
    """Should parse --login-path."""
    options = parse_args(["--login-path", "production"])
    assert options.connect_directly is True
    assert options.cli_profile is not None
    assert options.cli_profile.login_path == "production"


def test_defaults_file_flag() -> None:
    """Should parse --defaults-file."""
    options = parse_args(["--defaults-file", "/etc/mysql/my.cnf"])
    assert options.connect_directly is True
    assert options.cli_profile is not None
    assert options.cli_profile.option_file == "/etc/mysql/my.cnf"


def test_defaults_group_suffix_flag() -> None:
    """Should parse --defaults-group-suffix."""
    options = parse_args(["--defaults-file", "/etc/my.cnf", "--defaults-group-suffix", "_pay"])
    assert options.cli_profile is not None
    assert options.cli_profile.option_group == "_pay"


def test_ssl_mode_flag() -> None:
    """Should parse --ssl-mode."""
    options = parse_args(["-h", "db", "--ssl-mode", "VERIFY_CA", "--ssl-ca", "/ca.pem"])
    assert options.cli_profile is not None
    assert options.cli_profile.ssl is not None
    assert options.cli_profile.ssl.mode == "verify_ca"
    assert options.cli_profile.ssl.ca == "/ca.pem"


def test_profile_flag() -> None:
    """Should parse --profile for named profiles."""
    options = parse_args(["--profile", "Payments_prod"])
    assert options.connect_directly is True
    assert options.profile_name == "Payments_prod"
    assert options.cli_profile is None  # Profile looked up at runtime


def test_init_command_flag() -> None:
    """Should parse --init-command."""
    options = parse_args(["-h", "db", "--init-command", "SET SESSION wait_timeout=3600"])
    assert options.cli_profile is not None
    assert options.cli_profile.init_command == "SET SESSION wait_timeout=3600"


def test_default_values_when_only_host() -> None:
    """Only -h should produce defaults for everything else."""
    options = parse_args(["-h", "mydb"])
    assert options.cli_profile is not None
    assert options.cli_profile.host == "mydb"
    assert options.cli_profile.port == 3306
    assert options.cli_profile.username == ""
    assert options.cli_profile.compress is False
    assert options.cli_profile.connect_timeout == 10
    assert options.cli_profile.ssl is None
