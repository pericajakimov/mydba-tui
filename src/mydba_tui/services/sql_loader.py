"""
SQL file loader.

Loads SQL statements from .sql files in the package's sql/ directory
(``mydba_tui/sql/``). Keeping SQL separate from Python code makes it easier for
DBAs to review and optimize, and shipping it inside the package means the files
are available in installed wheels.
"""

from pathlib import Path

# Path to the sql/ directory inside the mydba_tui package. Keeping SQL inside
# the package means it ships with the wheel as package data.
_SQL_DIR = Path(__file__).parent.parent / "sql"

# Marker prepended to every application-generated statement so it can be
# recognized in the server's process list. User-entered SQL is never tagged.
_TAG = "/* mydba */"


def tag_sql(sql: str) -> str:
    """Prefix a statement with the mydba marker for process-list visibility.

    Apply this to application-generated SQL only. Never apply it to SQL the
    user wrote (e.g. SQL Workspace statements or a profile init command), which
    must run exactly as typed.

    Args:
        sql: The statement to tag.

    Returns:
        The statement prefixed with the mydba marker.
    """
    return f"{_TAG} {sql.lstrip()}"


def _strip_header_comments(text: str) -> str:
    """Remove leading ``--`` comment lines and blank lines from SQL text.

    The .sql files carry human-facing header comments (description, call site).
    Those are for readers of the repository; they should not be sent to the
    server, where they would clutter the process list. Only the leading comment
    block is removed — comments inside the statement body are preserved.
    """
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "" or stripped.startswith("--"):
            start = i + 1
            continue
        break
    return "\n".join(lines[start:]).strip()


def load_sql(relative_path: str) -> str:
    """Load a SQL statement from a .sql file, ready to send to the server.

    The file's leading comment header is stripped and the mydba tag is
    prepended, so the statement is identifiable in the process list without
    leaking the repository's documentation comments to the server.

    Args:
        relative_path: Path relative to the sql/ directory,
            e.g. "browser/schema_names.sql".

    Returns:
        The tagged SQL statement (header comments removed).

    Raises:
        FileNotFoundError: If the SQL file does not exist.
    """
    sql_path = _SQL_DIR / relative_path
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")
    raw = sql_path.read_text(encoding="utf-8")
    return tag_sql(_strip_header_comments(raw))
