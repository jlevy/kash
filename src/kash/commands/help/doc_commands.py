from __future__ import annotations

from kash.commands.help.welcome import welcome
from kash.config.logger import get_logger
from kash.docs.all_docs import DocSelection, all_docs
from kash.exec import kash_command
from kash.help.help_pages import print_see_also
from kash.shell.output.shell_output import console_pager, print_markdown

log = get_logger(__name__)


@kash_command
def manual(no_pager: bool = False, doc_selection: DocSelection = DocSelection.full) -> None:
    """
    Show the kash full manual with all help pages.
    """
    # TODO: Take an argument to show help for a specific command or action.

    from kash.help.help_pages import print_manual

    with console_pager(use_pager=not no_pager):
        print_manual(doc_selection)


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
                "check_system_tools",
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
                "check_system_tools",
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
