"""
Server package.

Contains components related to MySQL server discovery, server capabilities,
version detection, and server-specific feature handling.
"""

from mydba_tui.server.detection import ServerInfo, detect

__all__ = [
    "ServerInfo",
    "detect",
]
