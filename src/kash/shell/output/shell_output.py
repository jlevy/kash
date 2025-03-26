"""
Output to the shell UI. These are for user interaction, not logging.
"""

import contextvars
import textwrap
from collections.abc import Callable
from contextlib import contextmanager
from enum import Enum, auto

import rich
import rich.style
from flowmark import Wrap, fill_text
from flowmark.text_filling import DEFAULT_INDENT
from rich.console import Group, OverflowMethod, RenderableType
from rich.rule import Rule
from rich.style import Style
from rich.text import Text

from kash.config.logger import get_console
from kash.config.text_styles import (
    COLOR_HINT_DIM,
    COLOR_RESPONSE,
    COLOR_STATUS,
    CONSOLE_WRAP_WIDTH,
    HRULE_CHAR,
    STYLE_ASSISTANCE,
    STYLE_HELP,
    STYLE_HINT,
    format_success_emoji,
)
from kash.shell.output.kmarkdown import KMarkdown
from kash.utils.rich_custom.rich_indent import Indent
from kash.utils.rich_custom.rich_markdown_fork import Markdown

console = get_console()


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


print_context_var: contextvars.ContextVar[str] = contextvars.ContextVar("print_prefix", default="")
"""
Context variable override for print prefix.
"""


class PadStyle(Enum):
    INDENT = auto()
    PAD = auto()
    PAD_TOP = auto()


@contextmanager
def print_style(pad_style: PadStyle):
    """
    Context manager for print styles.
    """
    if pad_style == PadStyle.INDENT:
        token = print_context_var.set(DEFAULT_INDENT)
        try:
            yield
        finally:
            print_context_var.reset(token)
    elif pad_style == PadStyle.PAD:
        cprint()
        yield
        cprint()
    elif pad_style == PadStyle.PAD_TOP:
        cprint()
        yield
    else:
        raise ValueError(f"Unknown style: {pad_style}")


@contextmanager
def console_pager(use_pager: bool = True):
    """
    Use a Rich pager, if requested and applicable. Otherwise does nothing.
    """
    console = get_console()
    if console.is_interactive and use_pager:
        with console.pager(styles=True):
            yield
    else:
        yield

    PrintHooks.after_pager()


null_style = rich.style.Style.null()


def rich_print(
    *args: RenderableType,
    width: int | None = None,
    soft_wrap: bool | None = None,
    indent: str = "",
    raw: bool = False,
    overflow: OverflowMethod | None = "fold",
    **kwargs,
):
    """
    Print to the Rich console, either the global console or a thread-local
    override, if one is active. With `raw` true, we bypass rich formatting
    entirely and simply write to the console stream.
    """
    console = get_console()
    if raw:
        # TODO: Indent not supported in raw mode.
        text = " ".join(str(arg) for arg in args)
        end = kwargs.get("end", "\n")

        console._write_buffer()  # Flush any pending rich content first.
        console.file.write(text)
        console.file.write(end)
        console.file.flush()
    else:
        if len(args) == 0:
            renderable = ""
        elif len(args) == 1:
            renderable = args[0]
        else:
            renderable = Group(*args)

        if indent:
            renderable = Indent(renderable, indent=indent)

        console.print(renderable, width=width, soft_wrap=soft_wrap, overflow=overflow, **kwargs)


def cprint(
    message: RenderableType = "",
    *args,
    text_wrap: Wrap = Wrap.WRAP,
    style: str | Style | None = None,
    transform: Callable[[str], str] = lambda x: x,
    extra_indent: str = "",
    end="\n",
    width: int | None = None,
    raw: bool = False,
):
    """
    Main way to print to the shell. Wraps `rprint` with our additional
    formatting options for text fill and prefix.
    """
    empty_indent = extra_indent.strip()

    tl_prefix = print_context_var.get()
    if tl_prefix:
        extra_indent = tl_prefix + extra_indent

    if text_wrap.should_wrap and not width:
        width = CONSOLE_WRAP_WIDTH

    # Handle unexpected types gracefully.
    if not isinstance(message, (Text, Markdown, RenderableType)):
        message = str(message)

    if message:
        if isinstance(message, str):
            style = style or null_style
            text = message % args if args else message
            if text:
                filled_text = fill_text(
                    transform(text),
                    text_wrap,
                    extra_indent=extra_indent,
                    empty_indent=empty_indent,
                )
                rich_print(
                    Text(filled_text, style=style),
                    end=end,
                    raw=raw,
                    width=width,
                )
            elif extra_indent:
                rich_print(
                    Text(extra_indent, style=null_style),
                    end=end,
                    raw=raw,
                    width=width,
                )
        else:
            rich_print(
                message,
                end=end,
                indent=extra_indent,
                width=width,
            )
    else:
        # Blank line.
        rich_print(Text(empty_indent, style=null_style))


def print_markdown(
    doc_str: str,
    extra_indent: str = "",
):
    doc_str = str(doc_str)  # Convenience for lazy objects.

    cprint(KMarkdown(doc_str), extra_indent=extra_indent)


def print_status(
    message: str,
    *args,
    text_wrap: Wrap = Wrap.NONE,
    extra_indent: str = "",
):
    PrintHooks.before_status()
    cprint(
        message,
        *args,
        text_wrap=text_wrap,
        style=COLOR_STATUS,
        extra_indent=extra_indent,
    )
    PrintHooks.after_status()


def print_result(
    message: str,
    *args,
    text_wrap: Wrap = Wrap.NONE,
    extra_indent: str = "",
):
    cprint(
        message,
        *args,
        text_wrap=text_wrap,
        extra_indent=extra_indent,
    )


def print_help(message: str, *args, text_wrap: Wrap = Wrap.WRAP, extra_indent: str = ""):
    cprint(message, *args, text_wrap=text_wrap, style=STYLE_HELP, extra_indent=extra_indent)


def print_assistance(
    message: str | Text | Markdown, *args, text_wrap: Wrap = Wrap.NONE, extra_indent: str = ""
):
    cprint(
        message,
        *args,
        text_wrap=text_wrap,
        style=STYLE_ASSISTANCE,
        extra_indent=extra_indent,
        width=CONSOLE_WRAP_WIDTH,
    )


def print_code_block(
    message: str,
    *args,
    format: str = "",
    extra_indent: str = "",
):
    markdown = KMarkdown(f"```{format}\n{message}\n```")
    cprint(markdown, *args, text_wrap=Wrap.NONE, extra_indent=extra_indent)


def print_text_block(message: str | Text | Markdown, *args, extra_indent: str = ""):
    cprint(message, text_wrap=Wrap.WRAP_FULL, *args, extra_indent=extra_indent)


def print_response(message: str = "", *args, text_wrap: Wrap = Wrap.NONE, extra_indent: str = ""):
    with print_style(PadStyle.PAD):
        cprint(
            message,
            *args,
            text_wrap=text_wrap,
            style=COLOR_RESPONSE,
            extra_indent=extra_indent,
        )


def print_h1(heading: str):
    heading = heading.upper()
    text = Text(heading, style="markdown.h1")
    rich_print(text, justify="center", width=CONSOLE_WRAP_WIDTH)
    rich_print()


def print_h2(heading: str):
    heading = heading.upper()
    text = Text(heading, style="markdown.h2")
    rich_print(text, justify="center", width=CONSOLE_WRAP_WIDTH)
    rich_print()


def print_h3(heading: str):
    text = Text(heading, style="markdown.h3")
    rich_print(text)
    rich_print()


def print_h4(heading: str):
    text = Text(heading, style="markdown.h4")
    rich_print(text)


def print_hrule(title: str = "", full_width: bool = False, style: str | Style = COLOR_HINT_DIM):
    """
    Print a horizontal rule, optionally with a title.
    """
    rule = Rule(title=title, style=style)
    rich_print(rule, width=None if full_width else CONSOLE_WRAP_WIDTH)


from kash.config.logger import get_logger

log = get_logger(__name__)

DEBUG_SPACING = False  # Turn on for debugging print spacing/separators.


class PrintHooks(Enum):
    """
    Consolidate spacing and separators for consistent formatting of output, assistance,
    error messages, etc.
    """

    before_welcome = "before_welcome"
    after_interactive = "after_interactive"
    before_workspace_info = "before_workspace_info"
    before_command_run = "before_command_run"
    after_command_run = "after_command_run"
    before_status = "before_status"
    after_status = "after_status"
    before_shell_action_run = "before_action_run"
    after_shell_action_run = "after_action_run"
    before_log_action_run = "before_log_action_run"
    before_assistance = "before_assistance"
    after_assistance = "after_assistance"
    nonfatal_exception = "nonfatal_exception"
    before_done_message = "before_done_message"
    before_output = "before_output"
    after_output = "after_output"
    before_result = "before_result"
    after_result = "after_result"
    before_show_selection = "before_show_selection"
    before_suggest_actions = "before_suggest_actions"
    after_pager = "after_pager"
    before_search_help = "before_search_help"
    spacer = "spacer"
    hrule = "hrule"

    def nl(self) -> None:
        if DEBUG_SPACING:
            cprint(f"({HRULE_CHAR * 3} {self.value} {HRULE_CHAR * 3})", style=STYLE_HINT)
        else:
            cprint()

    def __call__(self) -> None:
        if self == PrintHooks.before_welcome:
            self.nl()
        elif self == PrintHooks.after_interactive:
            self.nl()
        elif self == PrintHooks.before_workspace_info:
            pass
        elif self == PrintHooks.before_command_run:
            self.nl()
        elif self == PrintHooks.after_command_run:
            pass
        elif self == PrintHooks.before_status:
            self.nl()
        elif self == PrintHooks.after_status:
            self.nl()
        elif self == PrintHooks.before_shell_action_run:
            pass
        elif self == PrintHooks.after_shell_action_run:
            print_hrule()
            self.nl()
        elif self == PrintHooks.before_log_action_run:
            self.nl()
        elif self == PrintHooks.before_assistance:
            self.nl()
        elif self == PrintHooks.after_assistance:
            self.nl()
        elif self == PrintHooks.nonfatal_exception:
            self.nl()
        elif self == PrintHooks.before_done_message:
            self.nl()
        elif self == PrintHooks.before_output:
            self.nl()
        elif self == PrintHooks.after_output:
            self.nl()
        elif self == PrintHooks.before_result:
            self.nl()
        elif self == PrintHooks.after_result:
            self.nl()
        elif self == PrintHooks.before_show_selection:
            pass
        elif self == PrintHooks.before_suggest_actions:
            self.nl()
        elif self == PrintHooks.after_pager:
            pass
        elif self == PrintHooks.before_search_help:
            print_hrule()
        elif self == PrintHooks.spacer:
            cprint()
        elif self == PrintHooks.hrule:
            print_hrule()
