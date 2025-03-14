from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kash.model.actions_model import Action


def kash_reload_all() -> tuple[dict[str, Callable], dict[str, type["Action"]]]:
    """
    Import all kash modules that define actions and commands.
    """
    from kash.exec.action_registry import reload_all_action_classes
    from kash.exec.command_registry import get_all_commands

    commands = get_all_commands()
    actions = reload_all_action_classes()

    return commands, actions
