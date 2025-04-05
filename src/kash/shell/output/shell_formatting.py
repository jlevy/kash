"""
Output to the shell UI. These are for user interaction, not logging.
"""

import textwrap

from flowmark import Wrap, fill_text
from rich.console import Group
from rich.text import Text

from kash.config.text_styles import (
    STYLE_HINT,
    format_success_emoji,
)
from kash.shell.output.kmarkdown import KMarkdown


def fill_rich_text(
    doc: str | Text, text_wrap: Wrap = Wrap.WRAP_INDENT, initial_column: int = 0
) -> str | Text:
    def do_fill(text: str) -> str:
        return fill_text(
            textwrap.dedent(text).strip(), text_wrap=text_wrap, initial_column=initial_column
        )

    if isinstance(doc, Text):
        doc.plain = do_fill(doc.plain)
    else:
        doc = do_fill(doc)

    return doc


def format_name_and_value(
    name: str | Text,
    doc: str | Text,
    extra_note: str | None = None,
    text_wrap: Wrap = Wrap.HANGING_INDENT,
) -> Text:
    if isinstance(name, str):
        name = Text(name, style="markdown.h4")
    doc = fill_rich_text(doc, text_wrap=text_wrap, initial_column=len(name) + 2)

    return Text.assemble(
        name,
        ((" " + extra_note, STYLE_HINT) if extra_note else ""),
        (": ", STYLE_HINT),
        doc,
    )


def format_name_and_description(
    name: str | Text,
    doc: str | Text,
    extra_note: str | None = None,
    text_wrap: Wrap = Wrap.WRAP_INDENT,
) -> Group:
    """
    Print a heading, with an optional hint colored note after the heading, and then
    a body. Useful for help pages etc. Body is Markdown unless it's already a Text
    object; then it's wrapped.
    """

    if isinstance(name, str):
        name = Text(name, style="markdown.h3")
    elif isinstance(name, Text) and not name.style:
        name.style = "markdown.h3"
    if isinstance(doc, str):
        body = KMarkdown(doc)
    else:
        body = fill_rich_text(doc, text_wrap=text_wrap)

    heading = Text.assemble(name, ((" " + extra_note, STYLE_HINT) if extra_note else ""), "\n")
    return Group(heading, body)


def format_paragraphs(*paragraphs: str | Text | Group) -> Group:
    text: list[str | Text | Group] = []
    for paragraph in paragraphs:
        if text:
            text.append("\n\n")
        text.append(paragraph)

    return Group(*text)


def format_success(message: str | Text) -> Text:
    return Text.assemble(format_success_emoji(True), message)


def format_failure(message: str | Text) -> Text:
    return Text.assemble(format_success_emoji(False), message)


def format_success_or_failure(
    value: bool, true_str: str | Text = "", false_str: str | Text = "", space: str = ""
) -> Text:
    """
    Format a success or failure message with an emoji followed by the true or false string.
    If false_str is not provided, it will be the same as true_str.
    """
    emoji = format_success_emoji(value)
    if true_str or false_str:
        return Text.assemble(emoji, space, true_str if value else (false_str or true_str))
    else:
        return emoji
