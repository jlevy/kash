from __future__ import annotations

import contextvars
from dataclasses import dataclass
from pathlib import Path

from kash.config.logger import get_logger
from kash.model.exec_model import RuntimeSettings
from kash.model.items_model import State
from kash.workspaces.workspace_dirs import enclosing_ws_dir, global_ws_dir

log = get_logger(__name__)

_current_settings: contextvars.ContextVar[RuntimeSettings | None] = contextvars.ContextVar(
    "current_runtime_settings", default=None
)
"""
Context variable that tracks the current runtime settings. Only used if it is
explicitly set with a `with runtime_settings(...):` block.
"""


def current_runtime_settings() -> RuntimeSettings:
    """
    Get the current runtime settings. Uses the ambient context var settings if
    set and otherwise infers the workspace from the current working directory
    with default runtime settings.
    """

    ambient_settings = _current_settings.get()
    if ambient_settings:
        return ambient_settings

    default_ws_dir = enclosing_ws_dir() or global_ws_dir()
    return RuntimeSettings(default_ws_dir)


@dataclass(frozen=True)
class WsContext:
    global_ws_dir: Path
    enclosing_ws_dir: Path | None
    override_dir: Path | None

    @property
    def current_ws_dir(self) -> Path:
        if self.override_dir:
            return self.override_dir
        elif self.enclosing_ws_dir:
            return self.enclosing_ws_dir
        else:
            return self.global_ws_dir


def current_ws_context() -> WsContext:
    """
    Context path info about the current workspace, including the global workspace
    directory, any workspace directory that encloses the current working directory,
    and override set via runtime settings.
    """

    override_dir = None
    ambient_settings = _current_settings.get()
    if ambient_settings:
        override_dir = ambient_settings.workspace_dir

    return WsContext(global_ws_dir(), enclosing_ws_dir(), override_dir)


@dataclass
class RuntimeSettingsManager:
    """
    Manage the context for executing actions, including `RuntimeSettings` and
    `Workspace`.

    This is a minimal base class for use as a context manager. Most functionality
    is still in `FileStore`.

    Workspaces may be detected based on the current working directory or explicitly
    set using a `with` block:
    ```
    ws = get_ws("my_workspace")
    with ws:
        # code that calls current_ws() will use this workspace
    ```
    """

    settings: RuntimeSettings

    def __enter__(self):
        self._token = _current_settings.set(self.settings)
        log.info("New runtime context: %s", self.settings)
        return self.settings

    def __exit__(self, exc_type, exc_val, exc_tb):
        _current_settings.reset(self._token)
        log.info("Exiting runtime context: %s", self.settings)


def kash_runtime(
    workspace_dir: Path | None,
    *,
    rerun: bool = False,
    refetch: bool = False,
    override_state: State | None = None,
    tmp_output: bool = False,
    no_format: bool = False,
    sync_to_s3: bool = False,
) -> RuntimeSettingsManager:
    """
    Set a specific kash execution context for a with block.

    This allows defining a workspace and other execution settings as the ambient
    context within the block.

    If `workspace_dir` is not provided, the current workspace will be inferred
    from the working directory or fall back to the global workspace.

    Example usage:
    ```
    with kash_runtime(ws_path, rerun=args.rerun) as runtime:
        runtime.workspace.log_workspace_info()
        # Perform actions.
    ```
    """
    from kash.workspaces.workspaces import current_ws

    if workspace_dir is None:
        workspace_dir = current_ws().base_dir

    settings = RuntimeSettings(
        workspace_dir=workspace_dir,
        rerun=rerun,
        refetch=refetch,
        override_state=override_state,
        tmp_output=tmp_output,
        no_format=no_format,
        sync_to_s3=sync_to_s3,
    )
    return RuntimeSettingsManager(settings=settings)
