import threading
from functools import cache
from pathlib import Path

from pydantic.dataclasses import dataclass

from kash.config.logger import get_logger
from kash.file_storage.file_store import FileStore

log = get_logger(__name__)


# Cache the file store per directory, since it takes a little while to load.
@cache
def load_or_init_file_store(base_dir: Path, is_sandbox: bool) -> FileStore:
    file_store = FileStore(base_dir, is_sandbox, auto_init=True)
    return file_store


@dataclass(frozen=True)
class WorkspaceInfo:
    name: str
    base_dir: Path
    is_sandbox: bool


class WorkspaceRegistry:
    def __init__(self):
        self._workspaces: dict[str, WorkspaceInfo] = {}
        self._lock = threading.RLock()

    def load(self, name: str, base_dir: Path | None = None, is_sandbox: bool = False) -> FileStore:
        """
        Load or create a workspace and register it. If path is given and the workspace
        does not exist, create it.
        """

        with self._lock:
            info = self._workspaces.get(name)

            if not info:
                if base_dir:
                    info = WorkspaceInfo(name, base_dir.resolve(), is_sandbox)
                    self._workspaces[name] = info
                    log.info("Registered workspace: %s -> %s", name, info)
                else:
                    raise ValueError(f"Workspace not found: {name}")

            return load_or_init_file_store(info.base_dir, info.is_sandbox)

    def get_by_name(self, name: str) -> WorkspaceInfo | None:
        with self._lock:
            return self._workspaces.get(name)

    def get_by_path(self, base_dir: Path) -> WorkspaceInfo | None:
        base_dir = base_dir.resolve()
        with self._lock:
            for info in self._workspaces.values():
                if info.base_dir == base_dir:
                    return info
            return None


# Global registry instance.
_registry = WorkspaceRegistry()


def get_workspace_registry() -> WorkspaceRegistry:
    return _registry
