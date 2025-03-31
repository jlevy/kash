from kash.exec.action_registry import look_up_action_class
from kash.exec.command_registry import CommandFunction, look_up_command
from kash.exec.shell_callable_action import ShellCallableAction
from kash.exec_model.commands_model import Command
from kash.exec_model.shell_model import ShellResult
from kash.model.actions_model import Action
from kash.utils.errors import InvalidInput


def look_up_command_or_action(name: str) -> CommandFunction | type[Action]:
    """
    Look up a command or action by name.
    """
    try:
        return look_up_command(name)
    except InvalidInput:
        return look_up_action_class(name)


def run_command_or_action(command: Command) -> ShellResult | None:
    """
    Run a generic command, which could be invoking the assistant, an action,
    or a built-in command function.

    Note this is one of two places we invoke commands and actions. We also use direct
    invocation in xonsh. But in both cases we do the same thing for each.
    """
    # Try looking first for commands with this name.
    try:
        func = look_up_command(command.name)
        return func(command.args, command.options)
    except InvalidInput:
        action_cls = look_up_action_class(command.name)
        return ShellCallableAction(action_cls)(command.args)
