from collections.abc import Callable

import rich
from flowmark import Wrap
from strif import single_line

from kash.config.logger import get_logger
from kash.config.text_styles import STYLE_HINT, STYLE_KEY
from kash.exec import kash_command
from kash.help import tldr_help
from kash.help.function_param_info import annotate_param_info
from kash.help.recommended_commands import RECOMMENDED_TLDR_COMMANDS
from kash.model.params_model import Param
from kash.shell.output.kerm_codes import IframePopover, TextTooltip
from kash.shell.output.shell_output import PrintHooks, console_pager, cprint, format_name_and_value
from kash.utils.errors import InvalidInput

log = get_logger(__name__)


@kash_command
def kerm_text_tooltip(text: str) -> None:
    """
    Show a tooltip in the Kerm terminal.
    """
    tooltip = TextTooltip(text=text)
    print(tooltip.as_osc(), end="")


@kash_command
def kerm_iframe_popover(url: str) -> None:
    """
    Show an iframe popover in the Kerm terminal.
    """
    popover = IframePopover(url=url)
    print(popover.as_osc(), end="")


@kash_command
def dump_tldr_snippets() -> None:
    """
    Dev task to run occasionally: Dump a few hundred TLDR snippet examples to a
    standard script file for use in kash tab completion.
    """
    tldr_help.dump_all_tldr_snippets()


@kash_command
def debug_tldr() -> None:
    """
    Debug task to dump TLDR snippets for a few commands.
    """
    log.message("TLDR cache dir: %s", tldr_help._cache_dir)
    log.message("TLDR cache timestamp file: %s", tldr_help._timestamp_file)
    log.message("TLDR cache location: %s", tldr_help._cache_location("en"))
    log.message("Should update TLDR cache: %s", tldr_help._should_update_cache())

    with console_pager():
        for command in RECOMMENDED_TLDR_COMMANDS:
            cprint(f"{command}", style=STYLE_KEY)
            cprint(f"description: {tldr_help.tldr_description(command)}")
            cprint(f"help: {tldr_help.tldr_help(command)}")
            cprint()
            cprint("parsed snippets:")
            for snippet in tldr_help.tldr_snippets(command):
                cprint(f"# {snippet.comment}")
                cprint(f"{snippet.command_line}")
            cprint()
            cprint()


@kash_command
def debug_completions() -> None:
    """
    Dump info on all xonsh completers.
    """
    from xonsh.built_ins import XSH

    def name_of(completer: Callable) -> str:
        module_name = completer.__module__ if hasattr(completer, "__module__") else "?"
        if hasattr(completer, "__name__"):
            return f"{module_name}.{completer.__name__}"
        elif hasattr(completer, "__class__"):
            return f"{module_name}.{completer.__class__.__name__}"
        else:
            return str(completer)

    def to_str(completer: Callable) -> str:
        return f"{name_of(completer)} (non_exclusive={getattr(completer, 'non_exclusive', False)})"

    cprint(f"{len(XSH.completers)} completers registered:")
    PrintHooks.spacer()

    for completer in XSH.completers.values():
        cprint(to_str(completer), text_wrap=Wrap.NONE, style=STYLE_KEY)
        if completer.__doc__:
            cprint(
                f"{single_line(completer.__doc__)}", text_wrap=Wrap.WRAP_INDENT, style=STYLE_HINT
            )


@kash_command
def debug_help() -> None:
    """
    Debug task to dump help for all commands and actions.
    """
    from kash.docs.all_docs import all_docs

    cprint(f"all_docs: {all_docs}", style=STYLE_KEY)

    cprint("\nhelp_topics:", style=STYLE_KEY)

    for topic in all_docs.help_topics.__dict__.keys():
        cprint(f"{topic}", text_wrap=Wrap.NONE)

    cprint("\nfaqs:")
    for faq in all_docs.faqs:
        cprint(f"{faq}", text_wrap=Wrap.NONE)

    cprint("\ncustom_command_infos:", style=STYLE_KEY)
    for cmd in all_docs.custom_command_infos:
        cprint(f"{cmd}", text_wrap=Wrap.NONE)

    cprint("\nstd_command_infos:", style=STYLE_KEY)
    for cmd in all_docs.std_command_infos:
        cprint(f"{cmd}", text_wrap=Wrap.NONE)

    cprint("\naction_infos:", style=STYLE_KEY)
    for action in all_docs.action_infos:
        cprint(f"{action}", text_wrap=Wrap.NONE)

    # cprint("\nrecipe_snippets:", style=STYLE_KEY)
    # for snippet in all_docs.recipe_snippets:
    #     cprint(f"{snippet}", text_wrap=Wrap.NONE)


@kash_command
def debug_command(command_or_action: str) -> None:
    """
    Debug task to dump info on a command or action.
    """
    from kash.exec.action_registry import get_all_actions_defaults
    from kash.exec.command_registry import get_all_commands

    def dump_params(param_info: list[Param]) -> None:
        for param in param_info:
            cprint(format_name_and_value(param.display, str(param)))
            cprint()

    try:
        command = get_all_commands()[command_or_action]
        param_info = annotate_param_info(command)
        cprint(format_name_and_value("Command", f"`{command_or_action}`"))
        cprint(format_name_and_value("Docstring", command.__doc__ or ""))
        cprint()
        dump_params(param_info)
        cprint()
        rich.inspect(command)
    except KeyError:
        try:
            action = get_all_actions_defaults()[command_or_action]
            cprint(format_name_and_value("Action", f"`{command_or_action}`"))
            cprint(format_name_and_value("Description", action.description or ""))
            cprint()
            dump_params(list(action.params))
            cprint()
            rich.inspect(action.tool_json_schema(), title="JSON Schema", docs=False)
            cprint()
            rich.inspect(action, title="Action Instance", docs=False)
        except KeyError:
            raise InvalidInput(f"No info found for {command_or_action}")


@kash_command
def reload_system() -> None:
    """
    Experimental! Reload the kash package and all its submodules. Also restarts
    the local the local server. Not perfect! But sometimes useful for development.
    """
    import kash
    from kash.local_server.local_server import restart_local_server
    from kash.utils.common.import_utils import recursive_reload

    module = kash
    exclude = ["kash.xontrib.kash_extension"]  # Don't reload the kash initialization.

    def filter_func(name: str) -> bool:
        if exclude:
            for excluded_module in exclude:
                if name == excluded_module or name.startswith(excluded_module + "."):
                    log.info("Excluding reloading module: %s", name)
                    return False
        return True

    package_names = recursive_reload(module, filter_func=filter_func)
    log.info("Reloaded modules: %s", ", ".join(package_names))
    log.message("Reloaded %s modules from %s.", len(package_names), module.__name__)

    restart_local_server()

    # TODO Re-register commands and actions.


@kash_command
def reload_commands_and_actions() -> None:
    """
    Reload all commands and actions. This can be needed to register newly imported
    Python files that define commands or actions with the shell.
    """
    from kash.xonsh_custom.load_into_xonsh import reload_shell_commands_and_actions
    from kash.xonsh_custom.shell_load_commands import log_command_action_info

    reload_shell_commands_and_actions()
    log_command_action_info()
