"""Tests for credential resolution logic.

Tests the logic that determines which credentials are available
from profiles, .my.cnf, and login_path before deciding whether
to prompt the user.
"""

from pathlib import Path
from unittest.mock import patch

from mydba_tui.connection.mycnf import MyCnfCredentials, read_mycnf_credentials
from mydba_tui.models.profile import Profile


def _resolve_credentials(profile: Profile, mycnf_creds: MyCnfCredentials) -> tuple[str, str]:
    """Simplified version of ProfilesScreen._resolve_credentials for testing.

    Uses provided MyCnfCredentials instead of reading files.
    """
    username = profile.username
    password = profile.password

    if profile.login_path:
        return username or "login_path", password or "login_path"

    if not username and mycnf_creds.user:
        username = mycnf_creds.user
    if not password and mycnf_creds.password:
        password = mycnf_creds.password

    return username, password


def test_profile_has_both() -> None:
    """Profile with username and password — no .my.cnf needed."""
    profile = Profile(name="t", host="h", username="admin", password="pass")
    creds = MyCnfCredentials()

    user, pw = _resolve_credentials(profile, creds)

    assert user == "admin"
    assert pw == "pass"


def test_profile_has_username_mycnf_has_password() -> None:
    """Username from profile, password from .my.cnf."""
    profile = Profile(name="t", host="h", username="admin")
    creds = MyCnfCredentials(password="from_cnf")

    user, pw = _resolve_credentials(profile, creds)

    assert user == "admin"
    assert pw == "from_cnf"


def test_mycnf_has_username_profile_has_password() -> None:
    """Username from .my.cnf, password from profile."""
    profile = Profile(name="t", host="h", password="stored_pass")
    creds = MyCnfCredentials(user="cnf_user")

    user, pw = _resolve_credentials(profile, creds)

    assert user == "cnf_user"
    assert pw == "stored_pass"


def test_mycnf_has_both() -> None:
    """Both from .my.cnf when profile has nothing."""
    profile = Profile(name="t", host="h")
    creds = MyCnfCredentials(user="cnf_user", password="cnf_pass")

    user, pw = _resolve_credentials(profile, creds)

    assert user == "cnf_user"
    assert pw == "cnf_pass"


def test_neither_has_credentials() -> None:
    """No credentials from anywhere — both empty (will prompt)."""
    profile = Profile(name="t", host="h")
    creds = MyCnfCredentials()

    user, pw = _resolve_credentials(profile, creds)

    assert user == ""
    assert pw == ""


def test_mycnf_has_user_only() -> None:
    """Only username from .my.cnf — password empty (will prompt for password)."""
    profile = Profile(name="t", host="h")
    creds = MyCnfCredentials(user="dba_user")

    user, pw = _resolve_credentials(profile, creds)

    assert user == "dba_user"
    assert pw == ""


def test_login_path_provides_both() -> None:
    """login_path set — assume it provides credentials."""
    profile = Profile(name="t", host="h", login_path="my_login")
    creds = MyCnfCredentials()

    user, pw = _resolve_credentials(profile, creds)

    assert user == "login_path"
    assert pw == "login_path"


def test_login_path_with_profile_username() -> None:
    """login_path with explicit username — use profile username."""
    profile = Profile(name="t", host="h", username="explicit", login_path="my_login")
    creds = MyCnfCredentials()

    user, pw = _resolve_credentials(profile, creds)

    assert user == "explicit"
    assert pw == "login_path"


def test_profile_username_overrides_mycnf() -> None:
    """Profile username should take priority over .my.cnf username."""
    profile = Profile(name="t", host="h", username="profile_user")
    creds = MyCnfCredentials(user="cnf_user", password="cnf_pass")

    user, pw = _resolve_credentials(profile, creds)

    assert user == "profile_user"
    assert pw == "cnf_pass"


def test_profile_password_overrides_mycnf() -> None:
    """Profile password should take priority over .my.cnf password."""
    profile = Profile(name="t", host="h", password="profile_pass")
    creds = MyCnfCredentials(user="cnf_user", password="cnf_pass")

    user, pw = _resolve_credentials(profile, creds)

    assert user == "cnf_user"
    assert pw == "profile_pass"


def test_real_mycnf_file_integration(tmp_path: Path) -> None:
    """Integration test: read actual .my.cnf file and resolve."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text("[client]\nuser=real_user\npassword=real_pass\n", encoding="utf-8")

    creds = read_mycnf_credentials(option_file=str(cnf))
    profile = Profile(name="t", host="h")

    user, pw = _resolve_credentials(profile, creds)

    assert user == "real_user"
    assert pw == "real_pass"


def test_real_mycnf_partial_integration(tmp_path: Path) -> None:
    """Integration: .my.cnf has user only, profile has nothing — need prompt for password."""
    cnf = tmp_path / ".my.cnf"
    cnf.write_text("[client]\nuser=only_user\n", encoding="utf-8")

    creds = read_mycnf_credentials(option_file=str(cnf))
    profile = Profile(name="t", host="h")

    user, pw = _resolve_credentials(profile, creds)

    assert user == "only_user"
    assert pw == ""  # Will need to prompt
