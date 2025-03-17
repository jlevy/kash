from rich.text import Text

from kash.config.logger import get_logger
from kash.config.text_styles import COLOR_HINT
from kash.docs.all_docs import all_docs
from kash.help.docstring_utils import parse_docstring
from kash.shell.output.shell_output import (
    PrintHooks,
    cprint,
    format_name_and_value,
    print_h2,
    print_hrule,
    print_markdown,
)

log = get_logger(__name__)


def print_builtin_commands_help(full_help: bool = False) -> None:
    from kash.exec.command_registry import get_all_commands
    from kash.help.command_help import print_command_function_help

    print_h2("Available Commands")
    cprint()

    if full_help:
        for command in get_all_commands().values():
            print_command_function_help(command, verbose=False)
            cprint()
            print_hrule()
    else:
        for command in get_all_commands().values():
            docstring = parse_docstring(command.__doc__ or "")
            short_docstring = (
                docstring.body.split("\n\n")[0] if docstring.body else "(no description)"
            )
            cprint(format_name_and_value(f"`{command.__name__}`", short_docstring))
            cprint()


def print_actions_help(full_help: bool = False) -> None:
    from kash.exec.action_registry import get_all_actions_defaults
    from kash.help.command_help import print_action_help

    print_h2("Available Actions")
    cprint()

    if full_help:
        actions = get_all_actions_defaults()
        for action in actions.values():
            print_action_help(action, verbose=False)
            cprint()
            print_hrule()
    else:
        for action in get_all_actions_defaults().values():
            short_description = (
                action.description.split("\n\n")[0] if action.description else "(no description)"
            )
            cprint(format_name_and_value(f"`{action.name}`", short_description))
            cprint()


def quote_item(item: str) -> str:
    if "`" not in item:
        return f"`{item}`"
    else:
        return item


def print_see_also(commands_or_questions: list[str]) -> None:
    from kash.local_server.local_url_formatters import local_url_formatter

    with local_url_formatter() as fmt:
        PrintHooks.spacer()
        cprint(
            Text.assemble(
                Text("See also: ", "markdown.emph"),
                Text.join(
                    Text(", ", COLOR_HINT),
                    (fmt.command_link(item) for item in commands_or_questions),
                ),
            )
        )


def print_manual() -> None:
    help_topics = all_docs.help_topics

    print_markdown(help_topics.what_is_kash)

    print_markdown(help_topics.progress)

    print_markdown(help_topics.getting_started)

    print_markdown(help_topics.tips_for_use_with_other_tools)

    print_markdown(help_topics.philosophy_of_kash)

    print_markdown(help_topics.kash_overview)

    print_markdown(help_topics.workspace_and_file_formats)

    print_markdown(help_topics.modern_shell_tool_recommendations)

    print_markdown(help_topics.faq)

    cprint()
    print_builtin_commands_help()

    cprint()
    print_actions_help()

    cprint()

    print_h2("Additional Help")

    cprint(
        "Use `help` for this help page or to get help on a command. "
        "Use `xonfig tutorial` for xonsh help."
    )

    cprint()
