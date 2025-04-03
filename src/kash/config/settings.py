import os
from enum import Enum
from functools import cache
from logging import DEBUG, ERROR, INFO, WARNING
from pathlib import Path
from typing import overload

from pydantic.dataclasses import dataclass

from kash.utils.common.atomic_var import AtomicVar

APP_NAME = "kash"

DOT_DIR = ".kash"

GLOBAL_WS_NAME = "global"


def get_global_kash_dir() -> Path:
    return Path(os.environ.get("KASH_DIR", "~/.local/kash")).expanduser().resolve()


@overload
def path_from_env(env_name: str, default: None) -> None: ...


@overload
def path_from_env(env_name: str, default: Path) -> Path: ...


def path_from_env(env_name: str, default: Path | None) -> Path | None:
    value = os.environ.get(env_name)
    if value:
        return Path(value).expanduser().resolve()
    else:
        return default.expanduser().resolve() if default else None


def get_ws_root_dir() -> Path:
    return path_from_env("KASH_WS_ROOT", Path("."))


def get_global_ws_dir() -> Path:
    kash_ws_dir = path_from_env("KASH_GLOBAL_WS", None)
    if kash_ws_dir:
        return kash_ws_dir
    else:
        docs_dir = Path("~/Documents").expanduser().resolve()
        if not docs_dir.exists():
            raise ValueError(
                f"Documents directory ({docs_dir}) does not exist; "
                "set KASH_GLOBAL_WS to specify a global workspace directory"
            )
        else:
            return docs_dir / APP_NAME / GLOBAL_WS_NAME


def get_mcp_ws_dir() -> Path | None:
    """
    Get the directory for the MCP workspace, if set.
    """
    mcp_dir = os.environ.get("KASH_MCP_WS")
    if mcp_dir:
        return Path(mcp_dir).expanduser().resolve()
    else:
        return None


def get_rcfile_path() -> Path:
    return Path("~/.kashrc").expanduser().resolve()


GLOBAL_LOGS_DIR = get_global_kash_dir() / "logs"


GLOBAL_CACHE_PATH = get_global_kash_dir() / "cache"
MEDIA_CACHE_NAME = "media"
CONTENT_CACHE_NAME = "content"

# TCP port 4440 and 4470+ are currently unassigned.
# https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml?search=444
# https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml?search=447

MCP_SERVER_PORT = 4440

LOCAL_SERVER_PORT_START = 4470
LOCAL_SERVER_PORTS_MAX = 30


SERVER_LOG_FILE = str(GLOBAL_LOGS_DIR / "{name}_{port}.log")


class LogLevel(Enum):
    debug = DEBUG
    info = INFO
    warning = WARNING
    message = WARNING  # Same as warning, just for important console messages.
    error = ERROR

    @classmethod
    def parse(cls, level_str: str):
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


DEFAULT_LOG_LEVEL = LogLevel.parse(os.environ.get("KASH_LOG_LEVEL", "warning"))


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


def find_rcfiles() -> list[Path]:
    """
    Find active rcfiles. Currently only supports one.
    """
    rcfile_path = get_rcfile_path()
    if rcfile_path.exists():
        return [rcfile_path]
    else:
        return []


@dataclass
class Settings:
    media_cache_dir: Path
    """The workspace media cache directory, for caching audio, video, and transcripts."""

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


@cache
def server_log_file_path(name: str, port: int | str) -> Path:
    # Use a different log file for each port (server instance).
    return resolve_and_create_dirs(SERVER_LOG_FILE.format(name=name, port=port))


# Initial default settings.
_settings = AtomicVar(
    Settings(
        # These default to the global but can be overridden by workspace settings.
        media_cache_dir=GLOBAL_CACHE_PATH / MEDIA_CACHE_NAME,
        content_cache_dir=GLOBAL_CACHE_PATH / CONTENT_CACHE_NAME,
        debug_assistant=True,
        default_editor="nano",
        file_log_level=LogLevel.info,
        console_log_level=DEFAULT_LOG_LEVEL,
        local_server_ports_start=LOCAL_SERVER_PORT_START,
        local_server_ports_max=LOCAL_SERVER_PORTS_MAX,
        local_server_port=0,
        mcp_server_port=MCP_SERVER_PORT,
        use_kerm_codes=False,
        use_nerd_icons=True,
    )
)


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
