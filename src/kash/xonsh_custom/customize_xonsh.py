from kash.config.setup import setup

setup(rich_logging=True)  # Set up logging first.

import time
from typing import Any, Callable, Dict, List, Type, TYPE_CHECKING, TypeVar

from xonsh.built_ins import XSH
from xonsh.prompt.base import PromptFields

from kash.commands.base_commands.general_commands import self_check
from kash.commands.help_commands import doc_commands, help_commands
from kash.config.init import kash_import_all
from kash.config.logger import get_logger
from kash.config.settings import check_kerm_code_support
from kash.exec.action_registry import get_all_action_classes
from kash.exec.command_registry import get_all_commands
from kash.exec.history import wrap_with_history
from kash.exec.shell_callable_action import ShellCallableAction
from kash.exec_model.shell_model import ShellResult
from kash.local_server.local_server import start_local_server
from kash.local_server.local_url_formatters import enable_local_urls
from kash.shell_output.shell_output import cprint, PrintHooks
from kash.shell_tools.exception_printing import wrap_with_exception_printing
from kash.shell_tools.function_wrapper import wrap_for_shell_args
from kash.shell_tools.native_tools import tool_check
from kash.shell_ui.shell_results import show_shell_result
from kash.version import get_version_name
from kash.workspaces import current_workspace
from kash.workspaces.workspace_output import post_shell_result
from kash.xonsh_custom.customize_prompt import get_prompt_info, kash_xonsh_prompt
from kash.xonsh_custom.xonsh_completers import load_completers
from kash.xonsh_custom.xonsh_modern_tools import modernize_shell

if TYPE_CHECKING:
    from kash.model.actions_model import Action


log = get_logger(__name__)


# Make type checker happy with xonsh globals:


def get_env(name: str) -> Any:
    return __xonsh__.env[name]  # type: ignore  # noqa: F821


def set_env(name: str, value: Any) -> None:
    __xonsh__.env[name] = value  # type: ignore  # noqa: F821


def unset_env(name: str) -> None:
    del __xonsh__.env[name]  # type: ignore  # noqa: F821


def set_alias(name: str, value: str | Callable) -> None:
    aliases[name] = value  # type: ignore  # noqa: F821


def update_aliases(new_aliases: Dict[str, Callable]) -> None:
    aliases.update(new_aliases)  # type: ignore  # noqa: F821


def is_interactive() -> bool:
    return get_env("XONSH_INTERACTIVE")


R = TypeVar("R")


def _wrap_handle_results(func: Callable[..., R]) -> Callable[[List[str]], None]:

    def command(args: List[str]) -> None:

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

        selections = current_workspace(silent=silent).selections
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


def _register_commands_in_shell(commands: Dict[str, Callable]):
    """
    Register all kash commands as xonsh commands.
    """
    kash_commands = {}

    # Override default ? command.
    kash_commands["?"] = "assist"

    # Override the default Python help command.
    # builtin.help must not be loaded or this won't work.
    set_alias("help", help_commands.help)
    # An extra name just in case `help` doesn't work.
    set_alias("kash_help", help_commands.help)
    # A backup for xonsh's built-in history command.
    set_alias("xhistory", aliases["history"])  # type: ignore  # noqa: F821

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


def _register_actions_in_shell(actions: Dict[str, Type["Action"]]):
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
    commands, actions = kash_import_all()
    _register_commands_in_shell(commands)
    _register_actions_in_shell(actions)


def _kash_workspace_str() -> str:
    return get_prompt_info().workspace_str


def _shell_interactive_setup():
    from kash.xonsh_custom.xonsh_completers import add_key_bindings

    # Set up a prompt field for the workspace string.
    fields = PromptFields(XSH)
    fields["workspace_str"] = _kash_workspace_str
    set_env("PROMPT_FIELDS", fields)

    # Set up the prompt and title template.
    set_env("PROMPT", kash_xonsh_prompt)
    set_env("TITLE", "kash - {workspace_str}")

    add_key_bindings()

    modernize_shell()


def _log_command_action_info():
    action_count = len(get_all_action_classes())
    command_count = len(get_all_commands())
    cprint(
        f"{command_count} commands and {action_count} actions currently loaded. "
        "Use `commands` and `actions` for details."
    )


def customize_xonsh():
    """
    Everything to customize xonsh for kash. This can be loaded via a xontrib.
    """

    if is_interactive():
        # Do first so in case there is an error, the shell prompt etc works as expected.
        _shell_interactive_setup()

        # Then do welcome first since init could take a few seconds.
        doc_commands.welcome()

        def load():
            load_start_time = time.time()

            reload_shell_commands_and_actions()

            load_time = time.time() - load_start_time
            log.info(f"Action and command loading took {load_time:.2f}s.")

            # Completers depend on commands and actions being loaded.
            load_completers()

            # TODO: Consider preloading but handle failure?
            # all_docs.load()

        load()
        # Another idea was to try to seem a little faster starting up when interactive
        # but doesn't seem worth it.
        # load_thread = threading.Thread(target=load)
        # load_thread.start()

        PrintHooks.after_interactive()

        self_check(brief=True)

        # Currently only Kerm supports our advanced UI with Kerm codes.
        supports_kerm_codes = check_kerm_code_support()
        if supports_kerm_codes:
            start_local_server()
            enable_local_urls(True)
        else:
            cprint(
                "If your terminal supports it, you may use `start_local_server` to enable local links."
            )

        cprint()
        _log_command_action_info()

        current_workspace()  # Validates and logs info for user.

        tool_check().warn_if_missing()

    else:
        reload_shell_commands_and_actions()

    log.info("kash %s loaded", get_version_name())
