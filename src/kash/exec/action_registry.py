from __future__ import annotations

from cachetools import Cache, cached
from strif import AtomicVar

from kash.config.logger import get_logger
from kash.model.actions_model import Action
from kash.utils.errors import InvalidInput

log = get_logger(__name__)

# Global registry of action classes.
action_classes: AtomicVar[dict[str, type[Action]]] = AtomicVar({})


# Want it fast to get the full list of actions (important for tab completions
# etc) but also easy to invalidate the cache when we register a new action.
_action_classes_cache = Cache(maxsize=float("inf"))
_action_instances_cache = Cache(maxsize=float("inf"))


def clear_action_cache():
    _action_classes_cache.clear()
    _action_instances_cache.clear()


def register_action_class(cls: type[Action]):
    """
    Register an action class.
    """
    with action_classes.updates() as ac:
        if cls.name in ac:
            log.warning(
                "Duplicate action name (defined twice by accident?): %s (%s)",
                cls.name,
                cls,
            )
        ac[cls.name] = cls

        clear_action_cache()


@cached(_action_classes_cache)
def get_all_action_classes() -> dict[str, type[Action]]:
    # Ensure actions are registered (lazy — only runs on first call).
    from kash.actions import ensure_actions_registered

    ensure_actions_registered()

    # Returns a copy for safety.
    ac = action_classes.copy()
    if len(ac) == 0:
        log.error("No actions found! Was there an import error?")

    return dict(ac)


def look_up_action_class(action_name: str) -> type[Action]:
    actions = get_all_action_classes()
    if action_name not in actions:
        raise InvalidInput(f"Action not found: `{action_name}`")
    return actions[action_name]


def refresh_action_classes() -> dict[str, type[Action]]:
    """
    Reload all action classes, refreshing the cache. Call after registering
    new action classes.
    """
    clear_action_cache()
    return get_all_action_classes()


@cached(_action_instances_cache)
def get_all_actions_defaults() -> dict[str, Action]:
    """
    This is an instance of all actions with *default* settings, for use in
    docs, info etc.
    """
    actions_map: dict[str, Action] = {}
    for cls in get_all_action_classes().values():
        try:
            action: Action = cls.create(None)
        except Exception as e:
            log.error("Error instantiating action %s: %s", cls, e)
            log.info("Details", exc_info=True)
            continue

        # Record the source path.
        action.__source_path__ = getattr(cls, "__source_path__", None)  # pyright: ignore

        actions_map[action.name] = action

    result = dict(sorted(actions_map.items()))

    return result
