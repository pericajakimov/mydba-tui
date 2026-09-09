"""
Users service.

Lists MySQL accounts with a logical group derived entirely in SQL
(sql/admin/users.sql), and fetches an account's grants on demand. All SQL is
written to the SQL log for transparency.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mydba_tui.logging import log_sql
from mydba_tui.services.sql_loader import load_sql, tag_sql

if TYPE_CHECKING:
    from mysql.connector.abstracts import MySQLConnectionAbstract
    from mysql.connector.pooling import PooledMySQLConnection

# Columns presented, in display order. Group is first, as requested.
USER_COLUMNS = [
    "Group",
    "User",
    "Host",
    "Locked",
    "Password Expired",
    "Password Changed",
    "Auth Plugin",
]

_SQL_FILE_USERS = "admin/users.sql"


def _str(val: Any) -> str:
    """Coerce a possibly-None/bytes value to a display string."""
    if val is None:
        return ""
    if isinstance(val, (bytes, bytearray)):
        try:
            return val.decode("utf-8", "replace")
        except Exception:
            return str(val)
    return str(val)


def _yn(val: Any) -> bool:
    """Interpret a MySQL Y/N (or locked flag) as a boolean."""
    return _str(val).strip().upper() in ("Y", "YES", "1", "TRUE")


@dataclass(slots=True)
class UserAccount:
    """A MySQL account with its derived group and summary flags.

    Attributes:
        group: The logical group derived by the SQL (e.g. Admin, ReadOnly).
        group_color: Optional colour for the group label; empty means the
            application should auto-assign one.
        user: The account user name.
        host: The account host.
        locked: Whether the account is locked.
        password_expired: Whether the account's password is expired.
        password_last_changed: When the password was last changed (may be empty).
        plugin: The authentication plugin.
    """

    group: str
    group_color: str
    user: str
    host: str
    locked: bool
    password_expired: bool
    password_last_changed: str
    plugin: str


def fetch_users(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
) -> list[UserAccount]:
    """Fetch all accounts with their derived group, ordered group/user/host.

    Best-effort: returns an empty list if the account tables are not readable
    (e.g. insufficient privileges or a non-standard server).

    Args:
        connection: Active MySQL connection.

    Returns:
        List of UserAccount, ordered by group, user, host.
    """
    sql = load_sql(_SQL_FILE_USERS)
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(sql)
        description = cursor.description or []
        col_names = [desc[0] for desc in description]
        raw_rows = cursor.fetchall()
    except Exception:
        col_names = []
        raw_rows = []
    finally:
        duration = time.perf_counter() - start
        log_sql(sql, duration, "administration.users")
        cursor.close()

    idx = {name.lower(): i for i, name in enumerate(col_names)}

    def _get(row: Any, key: str, pos: int) -> Any:
        i = idx.get(key.lower(), pos)
        return row[i] if i < len(row) else None

    accounts: list[UserAccount] = []
    for row in raw_rows:
        r: Any = row
        accounts.append(
            UserAccount(
                group=_str(_get(r, "group_name", 0)),
                group_color=_str(_get(r, "group_color", 1)),
                user=_str(_get(r, "user", 2)),
                host=_str(_get(r, "host", 3)),
                locked=_yn(_get(r, "account_locked", 4)),
                password_expired=_yn(_get(r, "password_expired", 5)),
                password_last_changed=_str(_get(r, "password_last_changed", 6)),
                plugin=_str(_get(r, "plugin", 7)),
            )
        )
    return accounts


def fetch_user_grants(
    connection: MySQLConnectionAbstract | PooledMySQLConnection,
    user: str,
    host: str,
) -> list[str]:
    """Fetch the grant statements for a single account, on demand.

    Uses SHOW GRANTS for the specific account (the one place per-account grant
    detail is appropriate). Best-effort: returns an empty list on error.

    Args:
        connection: Active MySQL connection.
        user: The account user name.
        host: The account host.

    Returns:
        The grant statements as a list of strings.
    """
    # Identifiers are quoted; escape any embedded quotes defensively.
    safe_user = user.replace("'", "''")
    safe_host = host.replace("'", "''")
    sql = tag_sql(f"SHOW GRANTS FOR '{safe_user}'@'{safe_host}'")
    start = time.perf_counter()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
    except Exception:
        rows = []
    finally:
        duration = time.perf_counter() - start
        log_sql(sql, duration, "administration.user_grants")
        cursor.close()

    grants: list[str] = []
    for row in rows:
        r: Any = row
        if r and r[0] is not None:
            grants.append(_str(r[0]))
    return grants
