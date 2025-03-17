from rich.box import SQUARE
from rich.panel import Panel
from rich.text import Text

from kash.config.logger import get_logger
from kash.config.text_styles import COLOR_HINT, CONSOLE_WRAP_WIDTH, LOGO, STYLE_LOGO
from kash.docs.all_docs import all_docs
from kash.exec import kash_command
from kash.help.help_pages import print_see_also
from kash.shell.output.shell_output import PrintHooks, console_pager, cprint, print_markdown
from kash.utils.rich_custom.rich_markdown_fork import Markdown
from kash.version import get_version_name

log = get_logger(__name__)


@kash_command
def welcome() -> None:
    """
    Print a welcome message.
    """

    help_topics = all_docs.help_topics
    version = get_version_name()
    # Create header with logo and right-justified version

    separator = " " + "─" * (CONSOLE_WRAP_WIDTH - len(LOGO) - len(version) - 2 - 3 - 3) + " "
    header = Text.assemble(
        Text(LOGO, style=STYLE_LOGO),
        Text(separator),
        Text(version, style=COLOR_HINT, justify="right"),
    )

    PrintHooks.before_welcome()
    cprint(
        Panel(
            Markdown(help_topics.welcome),
            title=header,
            title_align="left",
            border_style=COLOR_HINT,
            padding=(1, 1),
            box=SQUARE,
        )
    )


@kash_command
def manual(no_pager: bool = False) -> None:
    """
    Show the kash full manual with all help pages.
    """
    # TODO: Take an argument to show help for a specific command or action.

    from kash.help.help_pages import print_manual

    with console_pager(use_pager=not no_pager):
        print_manual()


@kash_command
def why_kash() -> None:
    """
    Show help on why kash was created.
    """
    help_topics = all_docs.help_topics
    with console_pager():
        print_markdown(help_topics.what_is_kash)
        print_markdown(help_topics.philosophy_of_kash)
        print_see_also(["help", "getting_started", "faq", "commands", "actions"])


@kash_command
def installation() -> None:
    """
    Show help on installing kash.
    """
    help_topics = all_docs.help_topics
    with console_pager():
        print_markdown(help_topics.installation)
        print_see_also(
            [
                "What is kash?",
                "What can I do with kash?",
                "getting_started",
                "What are the most important kash commands?",
                "commands",
                "actions",
                "check_tools",
                "faq",
            ]
        )


@kash_command
def getting_started() -> None:
    """
    Show help on getting started using kash.
    """
    help_topics = all_docs.help_topics
    with console_pager():
        print_markdown(help_topics.getting_started)
        print_see_also(
            [
                "What is kash?",
                "What can I do with kash?",
                "What are the most important kash commands?",
                "commands",
                "actions",
                "check_tools",
                "faq",
            ]
        )


@kash_command
def faq() -> None:
    """
    Show the kash FAQ.
    """
    help_topics = all_docs.help_topics
    with console_pager():
        print_markdown(help_topics.faq)

        print_see_also(["help", "commands", "actions"])


DOC_COMMANDS = [welcome, manual, why_kash, getting_started, faq]
