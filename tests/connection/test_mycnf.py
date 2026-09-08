"""Tests for .my.cnf parsing."""

from pathlib import Path

from mydba_tui.connection.mycnf import read_mycnf_credentials


def test_reads_user_and_password(tmp_path: Path) -> None:
    """Should read user and password from [client] section."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text("[client]\nuser=dba_user\npassword=secret123\n", encoding="utf-8")

    creds = read_mycnf_credentials(option_file=str(cnf))

    assert creds.user == "dba_user"
    assert creds.password == "secret123"


def test_reads_user_only(tmp_path: Path) -> None:
    """Should read user without password."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text("[client]\nuser=readonly\n", encoding="utf-8")

    creds = read_mycnf_credentials(option_file=str(cnf))

    assert creds.user == "readonly"
    assert creds.password == ""


def test_reads_password_only(tmp_path: Path) -> None:
    """Should read password without user."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text("[client]\npassword=s3cret\n", encoding="utf-8")

    creds = read_mycnf_credentials(option_file=str(cnf))

    assert creds.user == ""
    assert creds.password == "s3cret"


def test_reads_host_and_port(tmp_path: Path) -> None:
    """Should read host and port from [client] section."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text("[client]\nhost=db.internal\nport=3307\n", encoding="utf-8")

    creds = read_mycnf_credentials(option_file=str(cnf))

    assert creds.host == "db.internal"
    assert creds.port == "3307"


def test_no_client_section(tmp_path: Path) -> None:
    """Should return empty credentials if no [client] section."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text("[mysql]\nuser=other\n", encoding="utf-8")

    creds = read_mycnf_credentials(option_file=str(cnf))

    assert creds.user == ""
    assert creds.password == ""


def test_file_not_found() -> None:
    """Should return empty credentials if file doesn't exist."""
    creds = read_mycnf_credentials(option_file="/nonexistent/path/.my.cnf")

    assert creds.user == ""
    assert creds.password == ""


def test_group_suffix_overrides_client(tmp_path: Path) -> None:
    """Group suffix section should override [client] values."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text(
        "[client]\n"
        "user=default_user\n"
        "password=default_pass\n"
        "\n"
        "[client_payments]\n"
        "user=payments_dba\n"
        "password=payments_pass\n",
        encoding="utf-8",
    )

    creds = read_mycnf_credentials(option_file=str(cnf), option_group="_payments")

    assert creds.user == "payments_dba"
    assert creds.password == "payments_pass"


def test_group_suffix_partial_override(tmp_path: Path) -> None:
    """Group suffix should only override fields it defines."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text(
        "[client]\nuser=base_user\npassword=base_pass\n\n[client_reporting]\nuser=report_user\n",
        encoding="utf-8",
    )

    creds = read_mycnf_credentials(option_file=str(cnf), option_group="_reporting")

    assert creds.user == "report_user"
    assert creds.password == "base_pass"


def test_group_suffix_not_found(tmp_path: Path) -> None:
    """Missing group suffix section should fall back to [client]."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text("[client]\nuser=fallback\npassword=fb_pass\n", encoding="utf-8")

    creds = read_mycnf_credentials(option_file=str(cnf), option_group="_nonexistent")

    assert creds.user == "fallback"
    assert creds.password == "fb_pass"


def test_empty_file(tmp_path: Path) -> None:
    """An empty config file should return empty credentials."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text("", encoding="utf-8")

    creds = read_mycnf_credentials(option_file=str(cnf))

    assert creds.user == ""
    assert creds.password == ""


def test_special_characters_in_password(tmp_path: Path) -> None:
    """Passwords with special characters should be read correctly."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text(
        "[client]\nuser=admin\npassword=P@ss:w0rd#!{2024}\n",
        encoding="utf-8",
    )

    creds = read_mycnf_credentials(option_file=str(cnf))

    assert creds.password == "P@ss:w0rd#!{2024}"
