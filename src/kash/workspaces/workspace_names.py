import re
from pathlib import Path

from kash.config.logger import get_logger
from kash.errors import InvalidInput

log = get_logger(__name__)


def normalize_workspace_name(ws_name: str) -> str:
    return str(ws_name).strip().rstrip("/")


def check_strict_workspace_name(ws_name: str) -> str:
    ws_name = normalize_workspace_name(ws_name)
    if not re.match(r"^[\w.-]+$", ws_name):
        raise InvalidInput(
            f"Use an alphanumeric name (- and . also allowed) for the workspace name: `{ws_name}`"
        )
    return ws_name


def to_ws_name(path_or_name: str | Path) -> str:
    """
    Get the workspace name from a path or name.
    """
    path_or_name = str(path_or_name).strip().rstrip("/")
    if not path_or_name:
        raise InvalidInput("Workspace name is required.")

    path = Path(path_or_name)
    name = normalize_workspace_name(path.name)
    return name
