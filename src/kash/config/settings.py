from __future__ import annotations

import os
from enum import IntEnum
from functools import cache
from logging import DEBUG, ERROR, INFO, WARNING
from pathlib import Path
from typing import Literal

from pydantic.dataclasses import dataclass
from strif import AtomicVar

from kash.config.env_settings import KashEnv

APP_NAME = "kash"

DOT_DIR = ".kash"

GLOBAL_WS_NAME = "workspace"
"""Name of the global workspace."""

RECOMMENDED_API_KEYS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPGRAM_API_KEY",
    "GROQ_API_KEY",
]


def get_all_common_api_env_vars() -> list[str]:
    """
    Get all the common environment variables that are recommended to be set.
    """
    from clideps.env_vars.env_names import get_all_common_env_names

    return list(set(get_all_common_env_names() + RECOMMENDED_API_KEYS))


RECOMMENDED_PKGS = [
    "less",
    "eza",
    "ripgrep",
    "bat",
    "zoxide",
    "dust",
    "duf",
    "pygmentize",
    "hexyl",
    "ffmpeg",
    "imagemagick",
]


MEDIA_CACHE_NAME = "media"
CONTENT_CACHE_NAME = "content"

# TCP port 4440 and 4470+ are currently unassigned.
# https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml?search=444
# https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml?search=447

DEFAULT_MCP_SERVER_PORT = 4440

LOCAL_SERVER_PORT_START = 4470
LOCAL_SERVER_PORTS_MAX = 30


LOCAL_SERVER_LOG_NAME = "local_server"


LogLevelStr = Literal["debug", "info", "message", "warning", "error"]


class LogLevel(IntEnum):
    """
    Convenience enum for log levels with parsing and ordering.
    """

    debug = DEBUG
    info = INFO
    warning = WARNING
    message = WARNING  # Same as warning, just for important console messages.
    error = ERROR

    @classmethod
    def parse(cls, level_str: str | LogLevelStr | LogLevel) -> LogLevel:
        if isinstance(level_str, LogLevel):
            return level_str
        canon_name = level_str.strip().lower()
        if canon_name == "warn":
            canon_name = "warning"
        try:
            return cls[canon_name]
        except KeyError:
            raise ValueError(
                f"Invalid log level: `{level_str}`. Valid options are: {', '.join(f'`{name}`' for name in cls.__members__)}"
            )

    def __str__(self):
        return self.name


DEFAULT_LOG_LEVEL = LogLevel.parse(KashEnv.KASH_LOG_LEVEL.read_str(default="warning"))


def resolve_and_create_dirs(path: Path | str, is_dir: bool = False) -> Path:
    """
    Resolve a path to an absolute path, handling ~ for the home directory
    and creating any missing parent directories.
    """
    full_path = Path(path).expanduser().resolve()
    if not full_path.exists():
        if is_dir:
            os.makedirs(full_path, exist_ok=True)
        else:
            os.makedirs(full_path.parent, exist_ok=True)
    return full_path


def find_in_cwd_or_parents(filename: Path | str) -> Path | None:
    """
    Find the first existing Path (or None) for a given filename in the current directory or its parents.
    """
    if isinstance(filename, str):
        filename = Path(filename)
    path = Path(".").absolute()
    while path != Path("/"):
        file_path = path / filename
        if file_path.exists():
            return file_path
        path = path.parent
    return None


def _get_rcfile_path() -> Path:
    return _get_system_config_dir() / "kashrc"


def find_rcfiles() -> list[Path]:
    """
    Find active rcfiles. Currently only supports one.
    """
    rcfile_path = _get_rcfile_path()
    if rcfile_path.exists():
        return [rcfile_path]
    else:
        return []


@dataclass
class Settings:
    ws_root_dir: Path
    """A default root directory for kash workspaces (typically `~/Kash`)."""

    global_ws_dir: Path
    """The directory for the default global workspace."""

    system_config_dir: Path
    """The directory for system-wide configuration files."""

    media_cache_dir: Path
    """The workspace media cache directory, for caching audio, video, and transcripts."""

    system_logs_dir: Path
    """Default global and system logs directory (for server logs, etc)."""

    system_cache_dir: Path
    """Default global and system cache directory (for global media, content, etc)."""

    mcp_ws_dir: Path | None
    """The directory for the MCP workspace, if set."""

    local_server_log_path: Path
    """The path to the local server log."""

    content_cache_dir: Path
    """The workspace content cache directory, for caching web or local files."""
    # TODO: Separate workspace cached content (e.g. thumbnails) vs global files
    # (e.g. help embeddings).

    debug_assistant: bool
    """Convenience to allow debugging of full assistant prompts."""

    default_editor: str
    """The default editor to use for editing files."""

    console_log_level: LogLevel
    """The log level for console-based logging."""

    console_quiet: bool
    """If true, suppress non-logging console output."""

    file_log_level: LogLevel
    """The log level for file-based logging."""

    local_server_ports_start: int
    """The start of the range of ports to try to run the local server on."""

    local_server_ports_max: int
    """The maximum number of ports to try to run the local server on."""

    local_server_port: int
    """Actual port number the local server is running on."""

    mcp_server_port: int
    """Actual port number the MCP server is running on."""

    use_kerm_codes: bool
    """If true, use Kerm codes for enriching terminal output."""

    use_nerd_icons: bool
    """If true, use Nerd Icons in file listings. Requires a compatible font."""


ws_root_dir = Path("~/Kash").expanduser()


def _get_ws_root_dir() -> Path:
    """Default root directory for kash workspaces."""
    return KashEnv.KASH_WS_ROOT.read_path(default=ws_root_dir)


def _get_global_ws_dir() -> Path:
    kash_ws_dir = KashEnv.KASH_GLOBAL_WS.read_path(default=None)
    if kash_ws_dir:
        return kash_ws_dir
    else:
        return _get_ws_root_dir() / GLOBAL_WS_NAME


def get_system_logs_dir() -> Path:
    return KashEnv.KASH_SYSTEM_LOGS_DIR.read_path(default=_get_ws_root_dir() / "logs")


def _get_system_config_dir() -> Path:
    return Path("~/.config/kash").expanduser().resolve()


def _get_system_cache_dir() -> Path:
    return KashEnv.KASH_SYSTEM_CACHE_DIR.read_path(default=_get_ws_root_dir() / "cache")


def _get_mcp_ws_dir() -> Path | None:
    mcp_dir = KashEnv.KASH_MCP_WS.read_str(default=None)
    if mcp_dir:
        return Path(mcp_dir).expanduser().resolve()
    else:
        return None


@cache
def _get_local_server_log_path() -> Path:
    return resolve_and_create_dirs(get_system_logs_dir() / f"{LOCAL_SERVER_LOG_NAME}.log")


def _read_settings():
    return Settings(
        # Essential system settings for logs, workspaces, and configs:
        ws_root_dir=_get_ws_root_dir(),
        global_ws_dir=_get_global_ws_dir(),
        system_config_dir=_get_system_config_dir(),
        system_logs_dir=get_system_logs_dir(),
        system_cache_dir=_get_system_cache_dir(),
        mcp_ws_dir=_get_mcp_ws_dir(),
        local_server_log_path=_get_local_server_log_path(),
        # These default to the global but can be overridden by workspace settings.
        media_cache_dir=_get_system_cache_dir() / MEDIA_CACHE_NAME,
        content_cache_dir=_get_system_cache_dir() / CONTENT_CACHE_NAME,
        debug_assistant=True,
        default_editor="nano",
        file_log_level=LogLevel.info,
        console_log_level=DEFAULT_LOG_LEVEL,
        console_quiet=False,
        local_server_ports_start=LOCAL_SERVER_PORT_START,
        local_server_ports_max=LOCAL_SERVER_PORTS_MAX,
        local_server_port=0,
        mcp_server_port=DEFAULT_MCP_SERVER_PORT,
        use_kerm_codes=False,
        use_nerd_icons=True,
    )


# Initial default settings.
_settings = AtomicVar(_read_settings())


def configure_ws_and_settings(root_dir: Path):
    """
    Reset and reload all settings, deriving all paths from the new workspace
    root. Good if embedding kash in another app.
    """
    global ws_root_dir
    ws_root_dir = root_dir
    _settings.set(_read_settings())


def atomic_global_settings() -> AtomicVar[Settings]:
    """
    Read access to global settings.
    """
    return _settings


def global_settings() -> Settings:
    """
    Read-only access to global settings.
    """
    return atomic_global_settings().copy()


def check_kerm_code_support() -> bool:
    """
    Check if the terminal supports Kerm Codes.
    """
    use_kerm_codes = False
    term_program = os.environ.get("TERM_PROGRAM") or ""
    if term_program.lower() in ("kerm", "kyrm"):
        with atomic_global_settings().updates() as settings:
            settings.use_kerm_codes = True
            use_kerm_codes = True

    return use_kerm_codes
