from kash.config.logger import get_logger
from kash.help.help_types import CommandInfo, CommandType

log = get_logger(__name__)


def load_custom_command_info() -> list[CommandInfo]:
    from kash.config.logger import record_console
    from kash.exec.command_registry import CommandFunction, get_all_commands
    from kash.help.help_printing import print_command_function_help

    def command_info_for(command: CommandFunction) -> CommandInfo:
        with record_console() as console:
            print_command_function_help(command)
        help_page = console.export_text()
        return CommandInfo(
            command_type=CommandType.kash_command,
            command=command.__name__,
            description=command.__doc__ or "",
            help_page=help_page,
        )

    commands = [command_info_for(c) for c in get_all_commands().values()]

    log.info(f"Loaded info on {len(commands)} kash commands")

    return commands
