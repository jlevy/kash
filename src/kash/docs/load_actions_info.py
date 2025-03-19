from kash.config.logger import get_logger
from kash.help.help_types import CommandInfo, CommandType

log = get_logger(__name__)


def load_action_info() -> list[CommandInfo]:
    from kash.config.logger import record_console
    from kash.exec.action_registry import get_all_actions_defaults
    from kash.help.help_printing import print_action_help
    from kash.model.actions_model import Action

    def action_info_for(action: Action) -> CommandInfo:
        with record_console() as console:
            print_action_help(action)
        help_page = console.export_text()
        return CommandInfo(
            command_type=CommandType.kash_action,
            command=action.name,
            description=action.description,
            help_page=help_page,
        )

    actions = [action_info_for(a) for a in get_all_actions_defaults().values()]

    log.info(f"Loaded info on {len(actions)} kash actions")

    return actions
