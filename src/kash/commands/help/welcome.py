from rich.box import SQUARE
from rich.console import Group
from rich.panel import Panel

from kash.commands.help.logo import branded_box
from kash.config.text_styles import (
    COLOR_HINT,
)
from kash.docs.all_docs import all_docs
from kash.exec import kash_command
from kash.shell.output.shell_output import PrintHooks, cprint
from kash.shell.version import get_full_version_name
from kash.utils.rich_custom.rich_markdown_fork import Markdown


@kash_command
def welcome() -> None:
    """
    Print a welcome message.
    """

    help_topics = all_docs.help_topics
    version = get_full_version_name()
    # Create header with logo and right-justified version

    PrintHooks.before_welcome()
    cprint(
        branded_box(
            Group(Markdown(help_topics.welcome)),
            version,
        )
    )
    cprint(Panel(Markdown(help_topics.warning), box=SQUARE, border_style=COLOR_HINT))
