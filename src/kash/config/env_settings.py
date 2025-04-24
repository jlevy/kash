import os
from enum import Enum
from pathlib import Path
from typing import overload


class KashEnv(str, Enum):
    """
    Environment variable settings for kash. None are required, but these may be
    used to override default values.
    """

    KASH_LOG_LEVEL = "KASH_LOG_LEVEL"
    """The log level for console-based logging."""

    KASH_WS_ROOT = "KASH_WS_ROOT"
    """The root directory for kash workspaces."""

    KASH_GLOBAL_WS = "KASH_GLOBAL_WS"
    """The global workspace directory."""

    KASH_SYSTEM_LOGS_DIR = "KASH_SYSTEM_LOGS_DIR"
    """The directory for system logs."""

    KASH_SYSTEM_CACHE_DIR = "KASH_SYSTEM_CACHE_DIR"
    """The directory for system cache (caches separate from workspace caches)."""

    KASH_MCP_WS = "KASH_MCP_WS"
    """The directory for the workspace for MCP servers."""

    KASH_SHOW_TRACEBACK = "KASH_SHOW_TRACEBACK"
    """Whether to show tracebacks on actions and commands in the shell."""

    @overload
    def read_str(self) -> str | None: ...

    @overload
    def read_str(self, default: str) -> str: ...

    def read_str(self, default: str | None = None) -> str | None:
        """
        Get the value of the environment variable from the environment (with
        optional default).
        """
        return os.environ.get(self.value, default)

    @overload
    def read_path(self, default: None) -> None: ...

    @overload
    def read_path(self, default: Path) -> Path: ...

    def read_path(self, default: Path | None = None) -> Path | None:
        """
        Get the value of the environment variable as a resolved path (with
        optional default).
        """
        value = os.environ.get(self.value)
        if value:
            return Path(value).expanduser().resolve()
        else:
            return default.expanduser().resolve() if default else None

    def read_bool(self, default: bool = False) -> bool:
        """
        Get the value of the environment variable as a boolean.
        """
        value = str(os.environ.get(self.value, default) or "").lower()
        return bool(value and value != "0" and value != "false" and value != "no")
