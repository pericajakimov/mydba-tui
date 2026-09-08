"""Tests for the connection builder logic."""

from pathlib import Path
from unittest.mock import patch

from mydba_tui.connection.connector import _build_connect_kwargs
from mydba_tui.models.profile import Profile, SslConfig


def test_basic_kwargs() -> None:
    """Should build basic connection kwargs from profile."""
    profile = Profile(
        name="test",
        host="db.example.com",
        port=3306,
        username="admin",
    )

    kwargs = _build_connect_kwargs(profile, "secret")

    assert kwargs["host"] == "db.example.com"
    assert kwargs["port"] == 3306
    assert kwargs["username"] == "admin"
    assert kwargs["password"] == "secret"
    assert kwargs["autocommit"] is True
    assert kwargs["connection_timeout"] == 10


def test_runtime_password_overrides_profile() -> None:
    """Runtime password should take priority over profile password."""
    profile = Profile(name="test", host="db", username="u", password="stored")

    kwargs = _build_connect_kwargs(profile, "runtime")

    assert kwargs["password"] == "runtime"


def test_profile_password_used_when_no_runtime() -> None:
    """Profile password should be used when runtime password is empty."""
    profile = Profile(name="test", host="db", username="u", password="stored")

    kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["password"] == "stored"


def test_no_password_if_both_empty() -> None:
    """No password key if both profile and runtime are empty."""
    profile = Profile(name="test", host="db", username="u")

    kwargs = _build_connect_kwargs(profile, "")

    assert "password" not in kwargs


def test_compression_enabled() -> None:
    """Compress flag should be passed when enabled."""
    profile = Profile(name="test", host="db", compress=True)

    kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["compress"] is True


def test_compression_disabled_not_in_kwargs() -> None:
    """Compress should not be in kwargs when disabled."""
    profile = Profile(name="test", host="db", compress=False)

    kwargs = _build_connect_kwargs(profile, "")

    assert "compress" not in kwargs


def test_custom_timeout() -> None:
    """Custom connect_timeout should be passed."""
    profile = Profile(name="test", host="db", connect_timeout=30)

    kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["connection_timeout"] == 30


def test_default_database() -> None:
    """Default database should be passed when set."""
    profile = Profile(name="test", host="db", default_database="payments")

    kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["database"] == "payments"


def test_no_database_when_empty() -> None:
    """Database should not be in kwargs when not set."""
    profile = Profile(name="test", host="db")

    kwargs = _build_connect_kwargs(profile, "")

    assert "database" not in kwargs


def test_ssl_disabled() -> None:
    """SSL disabled mode should set ssl_disabled=True."""
    profile = Profile(name="test", host="db", ssl=SslConfig(mode="disabled"))

    kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["ssl_disabled"] is True


def test_ssl_required() -> None:
    """SSL required mode should not disable SSL."""
    profile = Profile(name="test", host="db", ssl=SslConfig(mode="required"))

    kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["ssl_disabled"] is False
    assert "ssl_verify_cert" not in kwargs


def test_ssl_verify_ca() -> None:
    """SSL verify_ca mode should enable cert verification."""
    profile = Profile(
        name="test",
        host="db",
        ssl=SslConfig(mode="verify_ca", ca="/path/ca.pem"),
    )

    kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["ssl_verify_cert"] is True
    assert kwargs["ssl_ca"] == "/path/ca.pem"


def test_ssl_verify_identity() -> None:
    """SSL verify_identity mode should enable identity verification."""
    profile = Profile(
        name="test",
        host="db",
        ssl=SslConfig(mode="verify_identity", ca="/ca.pem"),
    )

    kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["ssl_verify_cert"] is True
    assert kwargs["ssl_verify_identity"] is True


def test_ssl_cert_and_key() -> None:
    """SSL client cert and key should be passed."""
    profile = Profile(
        name="test",
        host="db",
        ssl=SslConfig(mode="required", cert="~/client.pem", key="~/client-key.pem"),
    )

    kwargs = _build_connect_kwargs(profile, "")

    assert "ssl_cert" in kwargs
    assert "ssl_key" in kwargs


def test_option_file_used(tmp_path: Path) -> None:
    """Option file should be passed when it exists."""
    cnf = tmp_path / "custom.cnf"
    cnf.write_text("[client]\nuser=file_user\n", encoding="utf-8")
    profile = Profile(name="test", host="db", option_file=str(cnf))

    kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["option_files"] == str(cnf)


def test_option_group_builds_groups(tmp_path: Path) -> None:
    """Option group should build [client, client<suffix>] groups."""
    cnf = tmp_path / "custom.cnf"
    cnf.write_text("[client]\nuser=u\n[client_pay]\npassword=p\n", encoding="utf-8")
    profile = Profile(name="test", host="db", option_file=str(cnf), option_group="_pay")

    kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["option_groups"] == ["client", "client_pay"]


def test_mycnf_fallback(tmp_path: Path) -> None:
    """Should fall back to ~/.my.cnf when no option_file or login_path."""
    profile = Profile(name="test", host="db")

    with patch("mydba_tui.connection.connector.Path.home", return_value=tmp_path):
        cnf = tmp_path / ".my.cnf"
        cnf.write_text("[client]\nuser=home_user\n", encoding="utf-8")

        kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["option_files"] == str(cnf)


def test_no_mycnf_fallback_when_missing(tmp_path: Path) -> None:
    """Should not add option_files when ~/.my.cnf doesn't exist."""
    profile = Profile(name="test", host="db")

    with patch("mydba_tui.connection.connector.Path.home", return_value=tmp_path):
        kwargs = _build_connect_kwargs(profile, "")

    assert "option_files" not in kwargs


def test_username_not_overridden_when_empty() -> None:
    """Username should not be in kwargs when not provided."""
    profile = Profile(name="test", host="db", username="")

    kwargs = _build_connect_kwargs(profile, "")

    assert "username" not in kwargs


def test_sets_program_name_conn_attr() -> None:
    """The connection reports program_name=mydba for the process list."""
    profile = Profile(name="test", host="db")

    kwargs = _build_connect_kwargs(profile, "")

    assert kwargs["conn_attrs"] == {"program_name": "mydba"}
