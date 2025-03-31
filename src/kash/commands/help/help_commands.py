from flowmark import Wrap

from kash.commands.help.doc_commands import manual
from kash.config.logger import get_logger
from kash.config.text_styles import STYLE_HINT
from kash.docs.all_docs import all_docs
from kash.exec import kash_command
from kash.exec.command_exec import look_up_command_or_action
from kash.help.help_lookups import look_up_source_code
from kash.help.help_pages import print_see_also
from kash.help.help_printing import print_explain_command
from kash.llm_utils import LLM
from kash.shell.output.shell_output import PrintHooks, console_pager, cprint
from kash.shell.utils.native_utils import ViewMode, view_file_native

log = get_logger(__name__)


@kash_command
def help(query: str | None = None, search: bool = False) -> None:
    """
    Top-level help command for kash. Get help on any kash command or action
    or a shell command (uses TLDR docs).

    Invoked by itself without arguments, `help` shows the manual (same as
    `manual`).

    With a query argument, it tries to look up help on that
    command or action or shell command, based on kash docs and TLDR docs
    (same as `explain`).

    If those fails, it sends the request to the assistant.

    You can use the `search` option to do a simple search of help docs
    and TLDR snippets.

    Note that if you want Python `help()` and not kash help, use the
    alias `pyhelp`.

    :param search: If true, does a simple search of help docs
       (same as `search_help`).
    """
    if not search and not query:
        manual()
    elif search:
        help_search(query)
    else:
        explain(query)


@kash_command
def commands(no_pager: bool = False, full: bool = False) -> None:
    """
    Show help on all kash commands.

    :param full: If true, show full help for each command.
    """
    from kash.help.help_pages import print_builtin_commands_help

    if full:
        with console_pager(use_pager=not no_pager):
            print_builtin_commands_help(full_help=True)
        print_see_also(["actions", "help", "faq", "What are the most important kash commands?"])
    else:
        print_builtin_commands_help(full_help=False)
        print_see_also(
            ["commands --full", "help", "faq", "What are the most important kash commands?"]
        )


@kash_command
def actions(no_pager: bool = False, full: bool = False) -> None:
    """
    Show help on the full list of currently loaded actions.

    :param full: If true, show full help for each action.
    """
    from kash.help.help_pages import print_actions_help

    if full:
        with console_pager(use_pager=not no_pager):
            print_actions_help(full_help=True)
            print_see_also(
                ["commands", "help", "faq", "What are the most important kash commands?"]
            )
    else:
        print_actions_help(full_help=False)
        print_see_also(
            ["actions --full", "help", "faq", "What are the most important kash commands?"]
        )


@kash_command
def source_code(name: str) -> None:
    """
    Show the source code for a kash command or action. Great to use when writing
    new actions or when asking LLMs to write new actions.
    """
    command_or_action = look_up_command_or_action(name)
    view_file_native(look_up_source_code(command_or_action), view_mode=ViewMode.console)


@kash_command
def explain(text: str, no_assistant: bool = False) -> None:
    """
    Give help on a command or action.  If `no_assistant` is True then will not use the
    assistant if the command or text is not recognized.
    """
    model = None if no_assistant else LLM.default_standard
    print_explain_command(text, assistant_model=model)


@kash_command
def help_search(text: str, max: int = 10, min_score: float = 0.33) -> None:
    """
    Search help docs.

    TODO: This currently only searches commands and snippets, but not the kash manual.
    """
    hits = all_docs.help_index.rank_docs(text, max, min_score)
    for hit in hits:
        PrintHooks.before_search_help()
        cprint(f"# {hit.relatedness:.2f} ({hit.doc_key})", style=STYLE_HINT)
        cprint(hit.doc, text_wrap=Wrap.NONE)
        PrintHooks.spacer()


HELP_COMMANDS = [
    help,
    manual,
    commands,
    actions,
]
