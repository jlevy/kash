from collections.abc import Callable
from functools import wraps
from typing import Any

from kash.exec_model.commands_model import Command
from kash.utils.file_formats.chat_format import ChatMessage, ChatRole, append_chat_message
from kash.workspaces import current_ws

_IGNORE_COMMANDS = ["history", "clear_history", "show", "help"]


def _history_ignore(command: Command) -> bool:
    return command.name in _IGNORE_COMMANDS


def record_command(command: Command):
    if _history_ignore(command):
        return

    ws = current_ws(silent=True)
    history_file = ws.base_dir / ws.dirs.shell_history_yml
    if isinstance(command, str):
        command_str = command
    else:
        command_str = command.command_str

    command_str = command_str.strip()
    if not command_str:
        return

    append_chat_message(history_file, ChatMessage(ChatRole.command, command_str))


def wrap_with_history(func: Callable) -> Callable:
    """
    Wrap a function to record the command in the shell history.
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        record_command(Command.assemble(func, args=args, options=kwargs))
        return func(*args, **kwargs)

    return wrapper
