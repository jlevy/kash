from collections.abc import Callable

from kash.config.logger import get_logger
from kash.model.items_model import Item
from kash.model.preconditions_model import Precondition
from kash.utils.common.atomic_var import AtomicVar

log = get_logger(__name__)

# Global registry of preconditions.
_preconditions: AtomicVar[dict[str, Precondition]] = AtomicVar({})


def kash_precondition(func: Callable[[Item], bool]) -> Precondition:
    """
    Decorator to register a function as a Precondition.
    The function should return a bool and/or raise `PreconditionFailure`.

    Example:
        @register_precondition
        def is_file(item: Item) -> bool:
            return item.is_file()
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
    Returns a copy of all registered preconditions.
    """
    # Return a copy for safety.
    return dict(_preconditions.copy())
