from collections.abc import Callable
from typing import overload

from kash.config.logger import get_logger
from kash.exec_model.shell_model import ShellResult
from kash.utils.common.atomic_var import AtomicVar
from kash.utils.errors import InvalidInput

log = get_logger(__name__)


CommandFunction = Callable[..., ShellResult] | Callable[..., None]
"""
A function that can be registered as a kash command. It can take any number
of args. It can return a `ShellResult` (for reporting exceptions or customizing
shell output) or return nothing (if it throws exceptions on errors).
"""

# Global registry of commands.
_commands: AtomicVar[dict[str, CommandFunction]] = AtomicVar({})
_has_logged = False


@overload
def kash_command(func: Callable[..., ShellResult]) -> Callable[..., ShellResult]: ...


@overload
def kash_command(func: Callable[..., None]) -> Callable[..., None]: ...


def kash_command(func: CommandFunction) -> CommandFunction:
    """
    Decorator to register a command.
    """
    with _commands.updates() as commands:
        if func.__name__ in commands:
            log.error("Command `%s` already registered; duplicate definition?", func.__name__)
        commands[func.__name__] = func
    return func


def register_all_commands() -> None:
    """
    Ensure all commands are registered and imported.
    """
    with _commands.updates() as commands:
        import kash.commands  # noqa: F401

        global _has_logged
        if not _has_logged:
            log.info("Command registry: %d commands registered.", len(commands))
            _has_logged = True


def get_all_commands() -> dict[str, CommandFunction]:
    """
    All commands, sorted by name.
    """
    register_all_commands()
    return dict(sorted(_commands.copy().items()))


def look_up_command(name: str) -> CommandFunction:
    """
    Look up a command by name.
    """
    with _commands.updates() as commands:
        cmd = commands.get(name)
        if not cmd:
            raise InvalidInput(f"Command `{name}` not found")
        return cmd
