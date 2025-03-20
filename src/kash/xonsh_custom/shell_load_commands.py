from kash.actions import get_loaded_kits
from kash.config.setup import setup
from kash.config.text_styles import COLOR_VALUE, STYLE_HINT

setup(rich_logging=True)  # Set up logging first.

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

from rich.text import Text

from kash.config.init import kash_reload_all
from kash.config.logger import get_logger
from kash.exec.action_registry import get_all_action_classes
from kash.exec.command_registry import get_all_commands
from kash.exec.history import wrap_with_history
from kash.exec.shell_callable_action import ShellCallableAction
from kash.exec_model.shell_model import ShellResult
from kash.shell.output.shell_output import PrintHooks, cprint
from kash.shell.ui.shell_results import show_shell_result
from kash.shell.utils.exception_printing import wrap_with_exception_printing
from kash.shell.utils.shell_function_wrapper import wrap_for_shell_args
from kash.workspaces import current_ws
from kash.workspaces.workspace_output import post_shell_result
from kash.xonsh_custom.xonsh_env import is_interactive, set_alias, set_env, update_aliases

if TYPE_CHECKING:
    from kash.model.actions_model import Action


log = get_logger(__name__)


R = TypeVar("R")


def _wrap_handle_results(func: Callable[..., R]) -> Callable[[list[str]], None]:
    def command(args: list[str]) -> None:
        PrintHooks.before_command_run()

        # Run the function.
        retval = func(args)

        res: ShellResult
        if isinstance(retval, ShellResult):
            res = retval
        else:
            res = ShellResult(retval)

        # Put result and selections in environment as $result, $selection, and $selections
        # for convenience for the user to access from the shell if needed.

        set_env("result", res.result)

        silent = not is_interactive()  # Don't log workspace info unless interactive.

        selections = current_ws(silent=silent).selections
        selection = selections.current
        set_env("selections", selections)
        set_env("selection", selection)

        PrintHooks.after_command_run()

        show_shell_result(res)
        post_shell_result(res)

        return None

    command.__name__ = func.__name__
    command.__doc__ = func.__doc__
    return command


def _register_commands_in_shell(commands: dict[str, Callable]):
    """
    Register all kash commands as xonsh commands.
    """
    from kash.commands.help import help_commands

    kash_commands = {}

    # Override default ? command.
    kash_commands["?"] = "assist"

    # Override the default Python help command.
    # builtin.help must not be loaded or this won't work.
    set_alias("help", help_commands.help)
    # An extra name just in case `help` doesn't work.
    set_alias("kash_help", help_commands.help)
    # A backup for xonsh's built-in history command.
    set_alias("xhistory", aliases["history"])  # pyright: ignore  # noqa: F821

    # TODO: Doesn't seem to reload modified Python?
    # def reload() -> None:
    #     xontribs.xontribs_reload(["kash"], verbose=True)
    #
    # _set_alias("reload", reload)

    # TODO: Move history to include all shell commands?
    for func in commands.values():
        kash_commands[func.__name__] = _wrap_handle_results(
            wrap_with_exception_printing(wrap_for_shell_args(wrap_with_history(func)))
        )

    update_aliases(kash_commands)


def _register_actions_in_shell(actions: dict[str, type["Action"]]):
    """
    Register all kash actions as xonsh commands.
    """
    callables = {}

    for action_cls in actions.values():
        callables[action_cls.name] = _wrap_handle_results(ShellCallableAction(action_cls))

    update_aliases(callables)


def reload_shell_commands_and_actions():
    """
    Import all commands and actions and register them in the shell.
    """
    commands, actions = kash_reload_all()
    _register_commands_in_shell(commands)
    _register_actions_in_shell(actions)


def log_command_action_info():
    kits = get_loaded_kits()
    action_count = len(get_all_action_classes())
    command_count = len(get_all_commands())
    cprint(
        Text.assemble(
            Text("Kits loaded: "),
            Text(
                f"{', '.join(kits.keys()) if kits else 'none'}", style=COLOR_VALUE if kits else ""
            ),
        )
    )
    cprint(
        Text.assemble(
            Text(f"{command_count} commands", style=COLOR_VALUE),
            Text(" and "),
            Text(f"{action_count} actions", style=COLOR_VALUE),
            Text(" loaded."),
        )
    )

    cprint("Use `commands`, `actions`, or `kits` for details.", style=STYLE_HINT)

    PrintHooks.spacer()
