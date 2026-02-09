from __future__ import annotations

from collections.abc import Callable

from strif import AtomicVar

from kash.config.logger import get_logger
from kash.model.items_model import Item
from kash.model.preconditions_model import Precondition

log = get_logger(__name__)

# Global registry of preconditions.
_preconditions: AtomicVar[dict[str, Precondition]] = AtomicVar({})


def kash_precondition(func: Callable[[Item], bool]) -> Precondition:
    """
    Decorator to register a function as a Precondition.
    The function should return a bool and/or raise `PreconditionFailure`.
    Returns an actual Precondition object, not the function, so that it's possible to
    do precondition algebra, e.g. `is_file & has_body`.

    Example:
        @kash_precondition
        def has_body(item: Item) -> bool:
            return item.has_body()
    """
    precondition = Precondition(func)

    with _preconditions.updates() as preconditions:
        if precondition.name in preconditions:
            log.warning(
                "Duplicate precondition name (defined twice by accident?): %s",
                precondition.name,
            )
        preconditions[precondition.name] = precondition

    return precondition


def get_all_preconditions() -> dict[str, Precondition]:
    """
    Returns a copy of all registered preconditions (in alphabetical order).
    """
    # Return a copy for safety, sorted by key.
    return dict(sorted(_preconditions.copy().items()))
