from pathlib import Path

from prettyfmt import fmt_lines, fmt_path

from kash.config.logger import get_logger
from kash.exec.action_registry import action_classes, refresh_action_classes
from kash.exec.command_registry import get_all_commands
from kash.utils.common.import_utils import Tallies, import_subdirs

log = get_logger(__name__)


def import_and_register(
    package_name: str | None,
    parent_dir: Path,
    subdir_names: list[str] | None = None,
    tallies: Tallies | None = None,
):
    """
    This hook can be used for auto-registering commands and actions from any
    subdirectory of a given package.

    Useful to call from `__init__.py` files to import a directory of code,
    auto-registering annotated commands and actions and also handles refreshing the
    action cache if new actions are registered.

    Usage:
    ```
    import_and_register(["subdir1", "subdir2"], __package__, Path(__file__).parent)
    ```
    """
    if not package_name:
        raise ValueError(f"Package name missing importing actions: {fmt_path(parent_dir)}")
    if tallies is None:
        tallies = {}

    with action_classes.updates() as ac:
        prev_command_count = len(get_all_commands())
        prev_action_count = len(ac)

        import_subdirs(package_name, parent_dir, subdir_names, tallies)

        new_command_count = len(get_all_commands()) - prev_command_count
        new_action_count = len(ac) - prev_action_count

        if new_action_count > 0:
            refresh_action_classes()

        log.info(
            "Loaded %s new commands and %s new actions in %s directories below %s:\n%s",
            new_command_count,
            new_action_count,
            len(tallies),
            fmt_path(parent_dir),
            fmt_lines(f"{k}: {v} files" for k, v in tallies.items()),
        )
