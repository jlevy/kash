from typing import Optional, Set

from funlog import log_calls

from prettyfmt import fmt_lines

from kash.config.logger import get_logger
from kash.errors import NoMatch
from kash.exec.precondition_defs import is_resource
from kash.model.items_model import Item
from kash.model.paths_model import StorePath
from kash.model.preconditions_model import Precondition
from kash.util.format_utils import fmt_loc
from kash.util.type_utils import not_none
from kash.workspaces import current_workspace

log = get_logger(__name__)


@log_calls()
def find_upstream_item(
    item: Item,
    precondition: Precondition,
    include_self: bool = True,
    visited: Optional[Set[StorePath]] = None,
) -> Item:
    """
    Breadth-first search up the `derived_from` provenance tree to find the first item that
    matches the precondition.
    """
    if not item.store_path:
        raise ValueError("Cannot trace provenance without a store path")
    store_path = StorePath(item.store_path)

    # Circular dependencies generally shouldn't happen but let's avoid them to be safe.
    if visited is None:
        visited = set()
    if store_path in visited:
        log.warning(
            "Detected a loop searching for upstream item with precondition `%s` at %s. Aborting this path.",
            precondition,
            fmt_loc(store_path),
        )
        raise NoMatch("Loop detected")

    visited.add(store_path)

    if include_self and precondition(item):
        return item

    if not item.relations.derived_from:
        raise NoMatch(f"Item must be derived from another item: {item}")

    workspace = current_workspace()

    log.info(
        "Finding items upstream of %s:\n%s",
        item.as_str_brief(),
        fmt_lines(item.relations.derived_from),
    )
    source_items = [workspace.load(StorePath(loc)) for loc in item.relations.derived_from]

    log.message("Looking for upstream item that matches precondition: %s", precondition)
    for source_item in source_items:
        source_path = not_none(source_item.store_path)
        if precondition(source_item):
            log.message(
                "Found source item that matches requirements: %s",
                fmt_loc(source_path),
            )
            return source_item
        else:
            log.message(
                "Item does not match precondition %s: %s",
                precondition,
                fmt_loc(source_path),
            )

    for source_item in source_items:
        try:
            return find_upstream_item(source_item, precondition, visited=visited)
        except NoMatch:
            pass

    raise NoMatch(
        f"Could not find a source item that fits the precondition {precondition}: {store_path}"
    )


def find_upstream_resource(item: Item) -> Item:
    return find_upstream_item(item, is_resource)
