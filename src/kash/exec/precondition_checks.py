import time
from collections.abc import Iterable

from funlog import format_duration

from kash.config.logger import get_logger
from kash.file_storage.file_store import FileStore
from kash.model.actions_model import Action
from kash.model.items_model import Item
from kash.model.paths_model import StorePath
from kash.model.preconditions_model import Precondition
from kash.utils.common.format_utils import fmt_loc
from kash.utils.errors import SkippableError

log = get_logger(__name__)


def actions_matching_paths(
    actions: Iterable[Action],
    ws: FileStore,
    paths: list[StorePath],
    include_no_precondition: bool = False,
) -> Iterable[Action]:
    """
    Which actions satisfy the preconditions for all the given paths.
    """

    def check_precondition(action: Action, store_path: StorePath) -> bool:
        if action.precondition:
            return action.precondition(ws.load(store_path))
        else:
            return include_no_precondition

    for action in actions:
        if all(check_precondition(action, store_path) for store_path in paths):
            yield action


def items_matching_precondition(
    ws: FileStore, precondition: Precondition, max_results: int = 0
) -> Iterable[Item]:
    """
    Yield items matching the given precondition, up to max_results if specified.
    """
    start_time = time.time()
    count = 0
    files_checked = 0
    for store_path in ws.walk_items():
        files_checked += 1
        if max_results > 0 and count >= max_results:
            break
        try:
            item = ws.load(store_path)
        except SkippableError:
            continue
        except Exception as e:
            log.info("Ignoring exception loading item %s: %s", fmt_loc(store_path), e)
            continue
        if precondition(item):
            yield item
            count += 1

    duration = time.time() - start_time
    if duration > 0.1:
        log.info(
            "Matched %s/%s items in %s (%s/s)",
            count,
            files_checked,
            format_duration(duration),
            int(files_checked / duration) if duration > 0 else 0,
        )
