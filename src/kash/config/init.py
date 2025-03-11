from typing import Callable, Dict, Tuple, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from kash.model.actions_model import Action


def kash_import_all() -> Tuple[Dict[str, Callable], Dict[str, Type["Action"]]]:
    """
    Import all kash modules that define actions and commands.
    """
    from kash.exec.action_registry import reload_all_action_classes
    from kash.exec.command_registry import get_all_commands

    commands = get_all_commands()
    actions = reload_all_action_classes()

    return commands, actions
