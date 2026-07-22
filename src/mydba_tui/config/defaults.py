"""
Default configuration values.

These constants define the initial settings used when no configuration
file exists. They represent sensible defaults for a first-time user.
"""

# Application defaults
DEFAULT_THEME = "textual-dark"
"""Default visual theme (Textual built-in theme name)."""

DEFAULT_LOG_LEVEL = "WARNING"
"""Default application log level."""

DEFAULT_SQL_LOG_ENABLED = True
"""Whether SQL logging is enabled by default."""

DEFAULT_PAGE_SIZE = 100
"""Default number of rows displayed in result sets."""

DEFAULT_REFRESH_INTERVAL = 3
"""Default monitoring refresh interval in seconds."""

DEFAULT_EXPORT_FORMAT = "csv"
"""Default export format."""
