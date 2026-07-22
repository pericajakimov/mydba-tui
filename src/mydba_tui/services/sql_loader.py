"""
SQL file loader.

Loads SQL statements from .sql files in the sql/ directory.
This keeps SQL separate from Python code for easier review
and optimization by DBAs.
"""

from pathlib import Path

# Path to the sql/ directory at the project root
_SQL_DIR = Path(__file__).parent.parent.parent.parent / "sql"


def load_sql(relative_path: str) -> str:
    """Load a SQL statement from a .sql file.

    Args:
        relative_path: Path relative to the sql/ directory,
            e.g. "browser/schemas.sql".

    Returns:
        The SQL text from the file.

    Raises:
        FileNotFoundError: If the SQL file does not exist.
    """
    sql_path = _SQL_DIR / relative_path
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")
    return sql_path.read_text(encoding="utf-8").strip()
