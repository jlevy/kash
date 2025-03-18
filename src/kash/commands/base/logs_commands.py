import os

from prettyfmt import fmt_lines

from kash.commands.base.basic_file_commands import trash
from kash.config.logger import get_log_settings, get_logger, reload_rich_logging_setup
from kash.config.settings import (
    LogLevel,
    atomic_global_settings,
    global_settings,
    server_log_file_path,
)
from kash.exec import kash_command
from kash.shell.output.shell_output import cprint, format_name_and_value, print_status
from kash.shell.utils.native_utils import tail_file
from kash.utils.common.format_utils import fmt_loc

log = get_logger(__name__)


@kash_command
def logs(follow: bool = False) -> None:
    """
    Page through the logs for the current workspace.

    :param follow: Follow the file as it grows.
    """
    tail_file(get_log_settings().log_file_path, follow=follow)


@kash_command
def clear_logs() -> None:
    """
    Clear the logs for the current workspace. Logs for the current workspace will be lost
    permanently!
    """
    log_path = get_log_settings().log_file_path
    if log_path.exists():
        with open(log_path, "w"):
            pass
    obj_dir = get_log_settings().log_objects_dir
    if obj_dir.exists():
        trash(obj_dir)
        os.makedirs(obj_dir, exist_ok=True)

    print_status("Logs cleared:\n%s", fmt_lines([fmt_loc(log_path)]))


@kash_command
def log_level(level: str | None = None, console: bool = False, file: bool = False) -> None:
    """
    Set or show the log level. Applies to both console and file log levels unless specified.

    :param level: The log level to set. If not specified, will show current level.
    :param console: Set console log level only.
    :param file: Set file log level only.
    """
    if not console and not file:
        console = True
        file = True

    if level:
        level_parsed = LogLevel.parse(level)
        with atomic_global_settings().updates() as settings:
            if console:
                settings.console_log_level = level_parsed
            if file:
                settings.file_log_level = level_parsed

        reload_rich_logging_setup()

    settings = get_log_settings()
    cprint(format_name_and_value("file_log_level", settings.log_file_level.name))
    cprint(format_name_and_value("console_log_level", settings.log_console_level.name))


@kash_command
def log_settings() -> None:
    """
    Show the current log settings.
    """
    settings = get_log_settings()
    cprint(format_name_and_value("log_dir", str(settings.log_dir)))
    cprint(format_name_and_value("log_file_path", str(settings.log_file_path)))
    cprint(format_name_and_value("log_objects_dir", str(settings.log_objects_dir)))
    cprint(format_name_and_value("log_file_level", settings.log_file_level.name))
    cprint(format_name_and_value("log_console_level", settings.log_console_level.name))
    cprint(
        format_name_and_value(
            "server_log_file", str(server_log_file_path(global_settings().local_server_port))
        )
    )
