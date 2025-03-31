from collections.abc import Callable, Sequence
from functools import wraps
from pathlib import Path
from typing import TypeVar

from frontmatter_format import new_yaml, yaml_util
from prettyfmt import fmt_lines
from pydantic import BaseModel, Field, PrivateAttr, field_serializer, field_validator

from kash.config.logger import get_logger
from kash.model.paths_model import StorePath
from kash.shell.utils.native_utils import native_trash
from kash.utils.common.format_utils import fmt_count_items, fmt_loc
from kash.utils.errors import InvalidInput, InvalidOperation

log = get_logger(__name__)

SH = TypeVar("SH", bound="SelectionHistory")
T = TypeVar("T")

SELECTION_HISTORY_MAX = 50

SELECTION_DISPLAY_MAX = 20


def persist_after(save_method: Callable[[SH], None]):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(self: SH, *args, **kwargs) -> T:
            result = func(self, *args, **kwargs)
            log.info("Saving selection history after %s().", func.__name__)
            save_method(self)
            return result

        return wrapper

    return decorator


class Selection(BaseModel):
    """
    A selection is a list of store paths for items in the workspace.
    """

    paths: list[StorePath] = Field(default_factory=list)

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @field_serializer("paths")
    def serialize_paths(self, paths) -> list[str]:
        return [p.display_str() for p in paths]

    @field_validator("paths", mode="before")
    @classmethod
    def deserialize_paths(cls, paths: list[str]) -> list[StorePath]:
        return [StorePath(p) for p in paths]

    def clear(self) -> None:
        """
        Clear the current selection.
        """
        self.paths.clear()

    def remove_values(self, targets: Sequence[StorePath]) -> None:
        """
        Remove specified paths from the current selection.
        """
        self.paths[:] = [p for p in self.paths if p not in targets]

    def replace_values(self, replacements: Sequence[tuple[StorePath, StorePath]]) -> None:
        """
        Replace paths in the current selection according to the replacement pairs.
        """
        for old_path, new_path in replacements:
            for idx, current_path in enumerate(self.paths):
                if current_path == old_path:
                    self.paths[idx] = new_path

    def as_str(self, max_lines: int = SELECTION_DISPLAY_MAX) -> str:
        lines = [
            f"{fmt_count_items(len(self.paths), 'item')}:",
            fmt_lines(fmt_loc(s) for s in self.paths[:max_lines]),
        ]
        if len(self.paths) > max_lines:
            lines.append(f"\n… and {len(self.paths) - max_lines} more items")
        return "\n".join(lines)

    def as_brief_str(self) -> str:
        return f"Selection({', '.join(fmt_loc(p) for p in self.paths)})"

    def __bool__(self) -> bool:
        return bool(self.paths)

    def __str__(self) -> str:
        return self.as_brief_str()


class SelectionHistory(BaseModel):
    """
    A history stack of selections that can result from outputs of a sequence of commands.
    """

    history: list[Selection] = Field(default_factory=list)
    current_index: int = 0

    _save_path: Path = PrivateAttr()
    _max_history: int = PrivateAttr()

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @classmethod
    def init(cls, save_path: Path, max_history: int = SELECTION_HISTORY_MAX) -> "SelectionHistory":
        """
        Initialize selection history, loading from save_path if it exists.
        """
        instance = cls()
        instance._save_path = save_path
        instance._max_history = max_history
        if save_path.exists():
            try:
                with save_path.open("r") as f:
                    data = new_yaml().load(f)
                instance = cls.model_validate(data)
                instance._save_path = save_path
                instance._max_history = max_history
            except Exception as e:
                log.warning(
                    f"Selection history can't be loaded, so will discard it (see trash): {save_path}: {e}"
                )
                native_trash(save_path)
                instance._save()

        return instance

    def _save(self) -> None:
        """
        Save the current full history.
        """
        data = self.model_dump()
        yaml_util.write_yaml_file(data, str(self._save_path))

    @persist_after(_save)
    def clear(self) -> None:
        """
        Clear the history.
        """
        self.history.clear()
        self.current_index = 0

    @persist_after(_save)
    def clear_future(self) -> None:
        """
        Clear history beyond the current position.
        """
        self._clear_future()

    def _clear_future(self) -> None:
        del self.history[self.current_index + 1 :]

    def _truncate(self) -> None:
        """
        Truncate history to the given length.
        """
        if self._max_history > 0 and len(self.history) > self._max_history:
            prev_len = len(self.history)
            del self.history[: -self._max_history]
            self.current_index -= prev_len - len(self.history)

    @property
    def current(self) -> Selection:
        """
        Get the current selection, or an empty selection if there is no history.
        """
        if not self.history:
            return Selection(paths=[])
        elif self.current_index < 0 or self.current_index >= len(self.history):
            fixed_index = max(0, len(self.history) - 1)
            log.warning(
                "Updating invalid selection index: %s -> %s", self.current_index, fixed_index
            )
            self.current_index = fixed_index
            self._save()
            return Selection(paths=[])
        else:
            return self.history[self.current_index]

    @persist_after(_save)
    def set_current(self, store_paths: list[StorePath]) -> None:
        """
        Set the current selection. If history is empty, adds a new selection.
        """
        if not self.history:
            self.push(Selection(paths=store_paths))
        else:
            self.history[self.current_index] = Selection(paths=store_paths)

    @persist_after(_save)
    def unselect_current(self, paths: Sequence[StorePath]) -> Selection:
        """
        Remove specified paths from the current selection.
        """
        if not self.history:
            raise InvalidOperation("No current selection")
        else:
            if paths:
                self.history[self.current_index].remove_values(paths)
            else:
                self.history[self.current_index].clear()
            return self.history[self.current_index]

    @persist_after(_save)
    def push(self, selection: Selection) -> None:
        """
        Append a new selection to history. If current_index is not at the end,
        discard the "future" history after the current position. If the current
        selection is empty, replace it instead of adding a new selection to history.
        """
        if not isinstance(selection, Selection):
            raise ValueError(f"Expected Selection, got {type(selection)}")

        self._clear_future()

        if len(selection.paths) == 0:
            log.info("Ignoring push of empty selection to history")
            return
        elif len(self.history) > 0 and self.history[-1] == selection:
            log.info(
                "Ignoring push of duplicate selection to history: %s", selection.as_brief_str()
            )
            return
        elif len(self.history) > 0 and len(self.history[-1].paths) == 0:
            log.info("Replacing empty current selection in history: %s", selection.as_brief_str())
            self.history[-1] = selection
        else:
            self.history.append(selection)
        self.current_index = len(self.history) - 1
        self._truncate()

    @persist_after(_save)
    def pop(self) -> Selection:
        """
        Remove the current selection from history and return it.
        """
        if not self.history:
            raise InvalidOperation("No current selection")
        else:
            selection = self.history.pop()
            self.current_index = max(0, self.current_index - 1)
            return selection

    @persist_after(_save)
    def previous(self, n: int = 1) -> Selection:
        """
        Move to the previous selection in history and return it.
        """
        if self.current_index - n < 0:
            if n == 1:
                raise InvalidOperation("No previous selection")
            else:
                raise InvalidOperation(f"No selection back {n} steps")
        self.current_index -= n
        return self.history[self.current_index]

    @persist_after(_save)
    def next(self, n: int = 1) -> Selection:
        """
        Move to the next selection in history and return it.
        """
        if self.current_index + n >= len(self.history):
            if n == 1:
                raise InvalidOperation("No next selection")
            else:
                raise InvalidOperation(f"No selection forward {n} steps")
        self.current_index += n
        return self.history[self.current_index]

    @persist_after(_save)
    def remove_values(self, targets: Sequence[StorePath]) -> None:
        """
        Remove specified paths from all selections.
        """
        for selection in self.history:
            selection.remove_values(targets)

        # Remove empty selections entirely. This happens for example if
        # we created a temporary item and then archived it.
        # Also adjust current_index if necessary so it stays valid.
        i = 0
        while i < len(self.history):
            if not self.history[i].paths:
                del self.history[i]
                if i <= self.current_index:
                    self.current_index = max(0, self.current_index - 1)
            else:
                i += 1

    @persist_after(_save)
    def replace_values(self, replacements: Sequence[tuple[StorePath, StorePath]]) -> None:
        """
        Replace paths in all selections according to the replacement pairs.
        """
        for selection in self.history:
            selection.replace_values(replacements)

    def previous_n(self, n: int, expected_size: int | None = None) -> list[Selection]:
        """
        Get the `n` previous selections (backwards and including the current position),
        with validation. If `expected_size` is provided, validates that each selection
        contains exactly `expected_size` paths.
        """
        if len(self.history) < n:
            raise InvalidOperation(
                f"Need {n} selections in history but only have {len(self.history)}"
            )

        if self.current_index + 1 < n:
            raise InvalidOperation(f"Need {n} selections before current position")

        selections = self.history[self.current_index - n + 1 : self.current_index + 1]

        if expected_size:
            for idx, selection in enumerate(selections):
                if len(selection.paths) != expected_size:
                    rel_idx = idx - n + 1  # Convert to relative index from current
                    raise InvalidInput(
                        f"Selection at position {rel_idx} has {len(selection.paths)} paths; exactly one path required"
                    )

        return selections
