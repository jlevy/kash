from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from prettyfmt import abbrev_obj
from pydantic.dataclasses import dataclass

from kash.config.logger import get_logger
from kash.file_storage.file_store import FileStore
from kash.model.items_model import State
from kash.workspaces.workspaces import get_ws

if TYPE_CHECKING:
    from kash.model.actions_model import Action

log = get_logger(__name__)


@dataclass(frozen=True)
class ExecContext:
    """
    An action and its context for execution. This is a good place for settings
    that apply to any action and are bothersome to pass as parameters.
    """

    action: "Action"  # noqa: UP037
    """The action being executed."""

    workspace_dir: Path
    """The workspace directory in which the action is being executed."""

    rerun: bool = False
    """If True, always run actions, even cacheable ones that have results."""

    refetch: bool = False
    """If True, will refetch items even if they are already in the content caches."""

    override_state: State | None = None
    """If specified, override the state of result items. Useful to mark items as transient."""

    tmp_output: bool = False
    """If True, will save output items to a temporary file."""

    no_format: bool = False
    """If True, will not normalize the output item's body text formatting (for Markdown)."""

    @property
    def workspace(self) -> FileStore:
        return get_ws(self.workspace_dir)

    @property
    def runtime_options(self) -> dict[str, str]:
        """Return non-default runtime options."""
        opts: dict[str, str] = {}
        # Only these two settings directly affect the output:
        if self.no_format:
            opts["no_format"] = "true"
        if self.override_state:
            opts["override_state"] = self.override_state.name
        return opts

    def __repr__(self):
        return abbrev_obj(self, field_max_len=80)
