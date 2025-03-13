from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Type

from cachetools import Cache, cached
from prettyfmt import fmt_lines, fmt_path

from kash.config.logger import get_logger
from kash.errors import InvalidInput
from kash.model.actions_model import Action
from kash.util.import_utils import import_subdirs, Tallies


log = get_logger(__name__)

# Global registry of action classes.
_action_classes: Dict[str, Type[Action]] = {}
_lock = Lock()


# Want it fast to get the full list of actions (important for tab completions
# etc) but also easy to invalidate the cache when we register a new action.
_action_classes_cache = Cache(maxsize=float("inf"))
_action_instances_cache = Cache(maxsize=float("inf"))


def clear_action_cache():
    _action_classes_cache.clear()
    _action_instances_cache.clear()


def register_action_class(cls: Type[Action]):
    """
    Register an action class.
    """
    with _lock:
        if cls.name in _action_classes:
            log.warning(
                "Duplicate action name (defined twice by accident?): %s (%s)",
                cls.name,
                cls,
            )
        _action_classes[cls.name] = cls

        clear_action_cache()


def import_action_subdirs(
    subdirs: List[str],
    package_name: Optional[str],
    parent_dir: Path,
    tallies: Optional[Tallies] = None,
):
    """
    Hook to call from `__init__.py` in a directory containing actions,
    so that they are auto-registered on import.

    Usage:
    ```
    import_action_subdirs(["subdir_name"], __package__, Path(__file__).parent)
    ```
    """
    if tallies is None:
        tallies = {}
    prev_count = len(_action_classes)

    if not package_name:
        raise ValueError(f"Package name missing importing actions: {fmt_path(parent_dir)}")

    import_subdirs(package_name, parent_dir, subdirs, tallies)
    reload_all_action_classes()

    log.message(
        "Loaded actions: %s new actions in %s directories:\n%s",
        len(_action_classes) - prev_count,
        len(tallies),
        fmt_lines(f"{k}: {v} files" for k, v in tallies.items()),
    )


@cached(_action_classes_cache)
def get_all_action_classes() -> Dict[str, Type[Action]]:
    if len(_action_classes) == 0:
        log.error("No actions found! Was there an import error?")

    # Return a copy for safety.
    return dict(_action_classes)


def look_up_action_class(action_name: str) -> Type[Action]:
    actions = get_all_action_classes()
    if action_name not in actions:
        raise InvalidInput(f"Action not found: `{action_name}`")
    return actions[action_name]


def reload_all_action_classes() -> Dict[str, Type[Action]]:
    clear_action_cache()
    return get_all_action_classes()


@cached(_action_instances_cache)
def get_all_actions_defaults() -> Dict[str, Action]:
    """
    This is an instance of all actions with *default* settings, for use in
    docs, info etc.
    """
    actions_map: Dict[str, Action] = {}
    for cls in get_all_action_classes().values():
        try:
            action: Action = cls.create(None)
        except Exception as e:
            log.error("Error instantiating action %s: %s", cls, e)
            log.info("Details", exc_info=True)
            continue

        # Record the source path.
        setattr(action, "__source_path__", getattr(cls, "__source_path__", None))

        actions_map[action.name] = action

    result = dict(sorted(actions_map.items()))

    return result
