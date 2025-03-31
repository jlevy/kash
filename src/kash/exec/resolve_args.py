from collections.abc import Sequence
from pathlib import Path
from typing import cast

from funlog import log_calls

from kash.config.logger import get_logger
from kash.exec_model.args_model import CommandArg
from kash.model.items_model import ItemType
from kash.model.paths_model import InvalidStorePath, StorePath, UnresolvedPath, parse_path_spec
from kash.utils.common.url import Locator, UnresolvedLocator, Url, is_url
from kash.utils.errors import InvalidInput, MissingInput
from kash.workspaces import current_ws

log = get_logger(__name__)


def resolve_locator_arg(locator_or_str: UnresolvedLocator) -> Locator:
    """
    Most general resolver for arguments to Locators.
    Resolve a path or URL argument to a Path, StorePath, or Url.
    """
    if isinstance(locator_or_str, StorePath):
        return locator_or_str
    elif not isinstance(locator_or_str, Path) and is_url(locator_or_str):
        return Url(locator_or_str)
    else:
        return resolve_path_arg(locator_or_str)


@log_calls(level="info", show_returns_only=True)
def resolve_path_arg(path_str: UnresolvedPath) -> Path | StorePath:
    """
    Resolve a string to a Path or if it is within the current workspace,
    a StorePath. Leaves already-resolved StorePaths and Paths unchanged.
    """
    if isinstance(path_str, str) and is_url(path_str):
        raise InvalidInput(f"Expected a path but got a URL: {path_str}")

    path = parse_path_spec(path_str)
    if path.is_absolute():
        return path
    else:
        try:
            store_path = current_ws().resolve_path(path)
            if store_path:
                return store_path
            else:
                return path
        except InvalidStorePath:
            return path


def assemble_path_args(*paths_or_strs: UnresolvedPath | None) -> list[StorePath | Path]:
    """
    Assemble paths or store paths from the current workspace, or the current
    selection if no paths are given. Fall back to treating values as plain
    Paths if values can't be resolved to store paths.
    """
    resolved = [resolve_path_arg(p) for p in paths_or_strs if p]
    if not resolved:
        ws = current_ws()
        resolved = ws.selections.current.paths
        if not resolved:
            raise MissingInput("No selection")
    return cast(list[StorePath | Path], resolved)


# TODO: Get more commands to work on files outside the workspace by importing them first.
def _check_store_paths(paths: Sequence[StorePath | Path]) -> list[StorePath]:
    """
    Check that all paths are store paths.
    """
    ws = current_ws()
    for path in paths:
        if not ws.exists(StorePath(path)):
            raise InvalidInput(f"Store path not found: {path}")
    return [StorePath(str(path)) for path in paths]


def assemble_store_path_args(*paths_or_strs: UnresolvedPath | None) -> list[StorePath]:
    """
    Assemble store paths from the current workspace, from args or the current
    selection if no args are given.
    """
    return _check_store_paths(assemble_path_args(*paths_or_strs))


def assemble_action_args(
    *paths_or_strs: UnresolvedPath | None, use_selection: bool = True
) -> tuple[list[CommandArg], bool]:
    """
    Assemble args for an action, as URLs, paths, or store paths.
    If indicated, use the current selection as fallback to find input paths.
    """
    resolved = [resolve_locator_arg(p) for p in paths_or_strs if p]
    if not resolved and use_selection:
        try:
            selection_args = current_ws().selections.current.paths
            return cast(list[CommandArg], selection_args), True
        except MissingInput:
            return [], False
    else:
        return cast(list[CommandArg], resolved), False


def resolvable_paths(paths: Sequence[StorePath | Path]) -> list[StorePath]:
    ws = current_ws()
    resolvable = list(filter(None, (ws.resolve_path(p) for p in paths)))
    return resolvable


def import_locator_args(
    *locators_or_strs: UnresolvedLocator,
    as_type: ItemType = ItemType.resource,
    reimport: bool = False,
) -> list[StorePath]:
    """
    Import locators into the current workspace.
    """
    locators = [resolve_locator_arg(loc) for loc in locators_or_strs]
    ws = current_ws()
    return ws.import_items(*locators, as_type=as_type, reimport=reimport)
