from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from kash.config.logger import get_logger
from kash.config.settings import global_settings, resolve_and_create_dirs
from kash.file_storage.metadata_dirs import MetadataDirs
from kash.utils.errors import InvalidInput

log = get_logger(__name__)


@cache
def global_ws_dir() -> Path:
    kb_path = resolve_and_create_dirs(global_settings().global_ws_dir, is_dir=True)
    log.debug("Global workspace path: %s", kb_path)
    return kb_path


def is_global_ws_dir(path: Path) -> bool:
    return path.resolve() == global_settings().global_ws_dir


def is_ws_dir(path: Path) -> bool:
    dirs = MetadataDirs(path, False)
    return dirs.is_initialized()


def enclosing_ws_dir(path: Path | None = None) -> Path | None:
    """
    Get the workspace directory enclosing the given path, or of the current
    working directory if no path is given.
    """
    if not path:
        path = Path(".")

    path = path.absolute()
    while path != Path("/"):
        if is_ws_dir(path):
            return path
        path = path.parent

    return None


def normalize_workspace_name(ws_name: str) -> str:
    return str(ws_name).strip().rstrip("/")


def check_strict_workspace_name(ws_name: str) -> str:
    ws_name = normalize_workspace_name(ws_name)
    if not re.match(r"^[\w.-]+$", ws_name):
        raise InvalidInput(
            f"Use an alphanumeric name (- and . also allowed) for the workspace name: `{ws_name}`"
        )
    return ws_name
