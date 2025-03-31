from os.path import basename
from pathlib import Path

from frontmatter_format import fmf_strip_frontmatter
from strif import copyfile_atomic

from kash.config.logger import get_logger
from kash.exec import kash_command
from kash.exec_model.shell_model import ShellResult
from kash.model.paths_model import StorePath
from kash.shell.ui.shell_results import shell_print_selection_history
from kash.utils.common.format_utils import fmt_loc
from kash.utils.errors import InvalidInput
from kash.utils.lang_utils.inflection import plural
from kash.workspaces import Selection, current_ws

log = get_logger(__name__)


@kash_command
def select(
    *paths: str,
    history: bool = False,
    last: int = 0,
    back: int = 0,
    forward: int = 0,
    previous: bool = False,
    next: bool = False,
    pop: bool = False,
    clear: bool = False,
    clear_future: bool = False,
) -> ShellResult:
    """
    Set or show the current selection.

    If no arguments are given, show the current selection.

    If paths are given, the new selection is pushed to the selection history.

    If any other flags are given, they show or modify the selection history.
    They must be used individually (and without paths).

    :param history: Show the full selection history.
    :param last: Show the last `last` selections in the history.
    :param back: Move back in the selection history by `back` steps.
    :param forward: Move forward in the selection history by `forward` steps.
    :param previous: Move back in the selection history to the previous selection.
    :param next: Move forward in the selection history to the next selection.
    :param pop: Pop the current selection from the history.
    :param clear: Clear the full selection history.
    :param clear_future: Clear all selections from history after the current one.
    """
    ws = current_ws()

    # TODO: It would be nice to be able to read stdin from a pipe but this isn't working rn.
    # You could then run `... | select --stdin` to select the piped input.
    # Globally we have THREAD_SUBPROCS=False to avoid hard-to-interrupt subprocesses.
    # But xonsh seems to hang with stdin unless we modify the spec to be threadable?
    # https://xon.sh/tutorial.html#callable-aliases
    # https://github.com/xonsh/xonsh/blob/main/xonsh/aliases.py#L1070
    # if stdin:
    #     paths = tuple(sys.stdin.read().splitlines())

    exclusive_flags = [history, last, back, forward, previous, next, pop, clear, clear_future]
    if sum(bool(f) for f in exclusive_flags) > 1:
        raise InvalidInput("Cannot combine multiple flags")
    if paths and any(exclusive_flags):
        raise InvalidInput("Cannot combine paths with other flags")

    if paths:
        store_paths = [StorePath(path) for path in paths]
        ws.selections.push(Selection(paths=store_paths))
        return ShellResult(show_selection=True)
    elif history:
        shell_print_selection_history(ws.selections)
        return ShellResult(show_selection=False)
    elif last:
        shell_print_selection_history(ws.selections, last=last)
        return ShellResult(show_selection=False)
    elif back:
        ws.selections.previous(back)
        shell_print_selection_history(ws.selections, last=last)
        return ShellResult(show_selection=False)
    elif forward:
        ws.selections.next(forward)
        shell_print_selection_history(ws.selections, last=last)
        return ShellResult(show_selection=False)
    elif previous:
        ws.selections.previous()
        shell_print_selection_history(ws.selections, last=last or 3)
        return ShellResult(show_selection=False)
    elif next:
        ws.selections.next()
        shell_print_selection_history(ws.selections, last=last or 3)
        return ShellResult(show_selection=False)
    elif pop:
        ws.selections.pop()
        return ShellResult(show_selection=True)
    elif clear:
        ws.selections.clear()
        return ShellResult(show_selection=True)
    elif clear_future:
        ws.selections.clear_future()
        return ShellResult(show_selection=True)
    else:
        return ShellResult(show_selection=True)


@kash_command
def unselect(*paths: str) -> ShellResult:
    """
    Remove items from the current selection. Handy if you've just selected some items and
    wish to unselect a few of them. Used without arguments, makes the current selection empty.
    """
    ws = current_ws()

    current_paths = ws.selections.current.paths.copy()
    new_paths = ws.selections.unselect_current([StorePath(path) for path in paths]).paths

    n_removed = len(current_paths) - len(new_paths)
    log.info(
        "Unselected %s %s, %s now selected.",
        n_removed,
        plural("item", n_removed),
        len(new_paths),
    )

    return ShellResult(show_selection=True)


@kash_command
def selections(
    last: int = 3,
    clear: bool = False,
    clear_future: bool = False,
) -> ShellResult:
    """
    Show the recent selection history. Same as `select --last=3` by default.
    """
    exclusive_flags = [clear, clear_future]
    exclusive_flag_count = sum(bool(f) for f in exclusive_flags)
    if exclusive_flag_count > 1:
        raise InvalidInput("Cannot combine multiple flags")
    if exclusive_flag_count:
        last = 0
    return select(last=last, clear=clear, clear_future=clear_future)


@kash_command
def prev_selection() -> ShellResult:
    """
    Move back in the selection history to the previous selection.
    Same as `select --previous`.
    """
    return select(previous=True)


@kash_command
def next_selection() -> ShellResult:
    """
    Move forward in the selection history to the next selection.
    Same as `select --next`.
    """
    return select(next=True)


@kash_command
def save(parent: str | None = None, to: str | None = None, no_frontmatter: bool = False) -> None:
    """
    Save the current selection to the given directory, or to the current directory if no
    target given.

    :param parent: The directory to save the files to. If not given, it will be the
        current directory.
    :param to: If only one file is selected, a name to save it as. If it exists, it will
        overwrite (and make a backup).
    :param no_frontmatter: If true, will not include YAML frontmatter in the output.
    """
    ws = current_ws()
    store_paths = ws.selections.current.paths

    def copy_file(store_path: StorePath, target_path: Path):
        path = ws.base_dir / store_path
        log.message("Saving: %s -> %s", fmt_loc(path), fmt_loc(target_path))
        copyfile_atomic(path, target_path, backup_suffix=".bak", make_parents=True)
        if no_frontmatter:
            fmf_strip_frontmatter(target_path)

    if len(store_paths) == 1 and to:
        target_path = Path(to)
        store_path = store_paths[0]
        copy_file(store_path, target_path)
    else:
        target_dir = Path(parent) if parent else Path(".")
        if not target_dir.exists():
            raise InvalidInput(f"Target directory does not exist: {target_dir}")

        for store_path in store_paths:
            target_path = target_dir / basename(store_path)
            copy_file(store_path, target_path)
