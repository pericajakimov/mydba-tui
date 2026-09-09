"""Tests for the users service."""

from typing import Any

from mydba_tui.services.users import fetch_user_grants, fetch_users

_COLS = [
    "group_name",
    "group_color",
    "user",
    "host",
    "account_locked",
    "password_expired",
    "password_last_changed",
    "plugin",
]


class _FakeCursor:
    def __init__(
        self, rows: list[tuple[Any, ...]], desc: list[Any], raise_on_execute: bool = False
    ) -> None:
        self._rows = rows
        self.description = desc
        self._raise = raise_on_execute
        self.executed: str | None = None

    def execute(self, sql: str) -> None:
        self.executed = sql
        if self._raise:
            raise RuntimeError("access denied")

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows

    def close(self) -> None:
        pass


class _FakeConnection:
    def __init__(
        self, rows: list[tuple[Any, ...]], desc: list[Any], raise_on_execute: bool = False
    ) -> None:
        self._rows = rows
        self._desc = desc
        self._raise = raise_on_execute
        self.last_cursor: _FakeCursor | None = None

    def cursor(self, buffered: bool = False) -> _FakeCursor:
        self.last_cursor = _FakeCursor(self._rows, self._desc, self._raise)
        return self.last_cursor


def _user_desc() -> list[tuple[str]]:
    return [(c,) for c in _COLS]


def test_fetch_users_maps_fields_and_flags() -> None:
    """Account rows map to UserAccount with Y/N flags interpreted."""
    rows = [
        (
            "System Users",
            "grey62",
            "root",
            "localhost",
            "N",
            "N",
            "2026-01-01 10:00:00",
            "caching_sha2_password",
        ),
        (
            "Personal Users",
            "",
            "john.doe",
            "%",
            "Y",
            "Y",
            "2026-02-02 12:00:00",
            "mysql_native_password",
        ),
    ]
    conn = _FakeConnection(rows, _user_desc())
    result = fetch_users(conn)  # type: ignore[arg-type]
    assert [(a.group, a.user) for a in result] == [
        ("System Users", "root"),
        ("Personal Users", "john.doe"),
    ]
    assert result[0].password_last_changed == "2026-01-01 10:00:00"
    assert result[0].locked is False
    assert result[1].locked is True
    assert result[1].password_expired is True


def test_fetch_users_empty_on_error() -> None:
    """Insufficient privileges / errors yield an empty list."""
    conn = _FakeConnection([], _user_desc(), raise_on_execute=True)
    assert fetch_users(conn) == []  # type: ignore[arg-type]


def test_fetch_user_grants_returns_lines_and_escapes() -> None:
    """SHOW GRANTS output is returned as a list; account name is escaped."""
    rows = [("GRANT SELECT ON *.* TO `app`@`%`",), ("GRANT USAGE ON *.* TO `app`@`%`",)]
    conn = _FakeConnection(rows, [("Grants",)])
    grants = fetch_user_grants(conn, "app", "%")  # type: ignore[arg-type]
    assert grants == ["GRANT SELECT ON *.* TO `app`@`%`", "GRANT USAGE ON *.* TO `app`@`%`"]
    assert conn.last_cursor is not None
    # Tagged and quoted for the specific account.
    assert "SHOW GRANTS FOR 'app'@'%'" in conn.last_cursor.executed  # type: ignore[operator]


def test_fetch_user_grants_empty_on_error() -> None:
    """A grants error yields an empty list, not an exception."""
    conn = _FakeConnection([], [("Grants",)], raise_on_execute=True)
    assert fetch_user_grants(conn, "app", "%") == []  # type: ignore[arg-type]
