"""
Settings that define the visual appearance of text outputs.
"""

import re
import shutil
from pathlib import Path

from rich.highlighter import RegexHighlighter, _combine_regex
from rich.style import Style
from rich.text import Text

## Text styles

LOGO_LARGE: str = (Path(__file__).parent / "logo.txt").read_text()

LOGO_NAME = "➤kash"

TAGLINE = "The knowledge agent shell"

TAGLINE_STYLED = Text.assemble(
    ("░ ", "bright_green"),
    (TAGLINE.upper(), "bold bright_green"),
    (" ░", "bright_green"),
)

LOGO_SPACER = Text.assemble(
    ("░ ", "bright_green"),
    " " * len(TAGLINE),
    (" ░", "bright_green"),
)


## Settings

TERMINAL_SIZE = shutil.get_terminal_size()

CONSOLE_WRAP_WIDTH = TERMINAL_SIZE.columns if 0 < TERMINAL_SIZE.columns < 88 else 88
"""
Default wrap width for console content. Aim to match our default
Markdown wrap width unless the terminal is too narrow.
"""

SPINNER = "dots12"
"""Progress spinner. For a list, use `python -m rich.spinner`."""

BAT_THEME = "Coldark-Dark"

BAT_STYLE = "header-filename,header-filesize,grid,changes"


## Colors

COLOR_PLAIN = "default"
COLOR_LINK = "cyan"
COLOR_SUCCESS = "green"
COLOR_FAILURE = "bright_red"
COLOR_WARN = "bright_red"
COLOR_ERROR = "bright_red"
COLOR_EXTRA = "bright_blue"
COLOR_SELECTION = "bright_yellow"
COLOR_STATUS = "yellow"
COLOR_COMMENT = "bright_black"
COLOR_RESULT = "default"
COLOR_RESPONSE = "bright_blue"
COLOR_SUGGESTION = "bright_blue"
COLOR_LITERAL = "bright_blue"
COLOR_GREEN = "bright_green"
COLOR_KEY = "bright_blue"
COLOR_VALUE = "cyan"
COLOR_PATH = "cyan"
COLOR_HINT = "bright_black"
COLOR_HINT_DIM = "dim bright_black"
COLOR_SKIP = "green"
COLOR_TASK = "magenta"
COLOR_SAVED = "blue"
COLOR_TIMING = "bright_black"
COLOR_CALL = "bright_yellow"

# Colors for quantity formatting, like file sizes or ages.
COLOR_SIZE1 = "bright_black"
COLOR_SIZE2 = "blue"
COLOR_SIZE3 = "cyan"
COLOR_SIZE4 = "bright_green"
COLOR_SIZE5 = "yellow"
COLOR_SIZE6 = "bright_red"


## Styles

STYLE_LOGO = "bold magenta"
STYLE_HEADING = "bold bright_green"
STYLE_HELP = "italic bright_blue"
STYLE_ASSISTANCE = "italic bright_blue"
STYLE_HINT = f"italic {COLOR_HINT}"
STYLE_EMPH = "bright_green"
STYLE_KEY = "bold bright_blue"
STYLE_CODE = "bold bright_cyan"
# For completions:
STYLE_KASH_COMMAND = "bold black"
STYLE_HELP_QUESTION = "italic bold black"

STYLE_SIZE1 = Style(color=COLOR_SIZE1)
STYLE_SIZE2 = Style(color=COLOR_SIZE2)
STYLE_SIZE3 = Style(color=COLOR_SIZE3, bold=True)
STYLE_SIZE4 = Style(color=COLOR_SIZE4, bold=True)
STYLE_SIZE5 = Style(color=COLOR_SIZE5, bold=True)
STYLE_SIZE6 = Style(color=COLOR_SIZE6, bold=True)


## Rich styles

RICH_STYLES = {
    "plain": COLOR_PLAIN,
    "link": COLOR_LINK,
    "success": COLOR_SUCCESS,
    "failure": COLOR_FAILURE,
    "warn": COLOR_WARN,
    "error": COLOR_ERROR,
    "extra": COLOR_EXTRA,
    "selection": COLOR_SELECTION,
    "status": COLOR_STATUS,
    "comment": COLOR_COMMENT,
    "result": COLOR_RESULT,
    "response": COLOR_RESPONSE,
    "suggestion": COLOR_SUGGESTION,
    "literal": COLOR_LITERAL,
    "key": COLOR_KEY,
    "value": COLOR_VALUE,
    "path": COLOR_PATH,
    "hint": COLOR_HINT,
    "hint_dim": COLOR_HINT_DIM,
    "skip": COLOR_SKIP,
    "task": COLOR_TASK,
    "saved": COLOR_SAVED,
    "timing": COLOR_TIMING,
    "call": COLOR_CALL,
    "logo": STYLE_LOGO,
    "heading": STYLE_HEADING,
    "help": STYLE_HELP,
    "assistance": STYLE_ASSISTANCE,
    "emph": STYLE_EMPH,
    "code": STYLE_CODE,
    "kash_command": STYLE_KASH_COMMAND,
    "help_question": STYLE_HELP_QUESTION,
    "size1": STYLE_SIZE1,
    "size2": STYLE_SIZE2,
    "size3": STYLE_SIZE3,
    "size4": STYLE_SIZE4,
    "size5": STYLE_SIZE5,
    "size6": STYLE_SIZE6,
    "markdown.paragraph": Style(),
    "markdown.text": Style(),
    "markdown.em": Style(italic=True),
    "markdown.emph": Style(italic=True),  # For commonmark backwards compatibility
    "markdown.strong": Style(bold=True),
    # Add bgcolor="black" or underline=True?
    "markdown.code": Style(bold=True, color="cyan"),
    "markdown.code_block": Style(color="cyan"),
    "markdown.block_quote": Style(color="bright_yellow"),
    "markdown.list": Style(color="cyan"),
    "markdown.item": Style(),
    "markdown.item.bullet": Style(color="magenta", bold=True),
    "markdown.item.number": Style(color="magenta", bold=True),
    "markdown.hr": Style(color=COLOR_HINT),
    "markdown.h1.border": Style(),
    "markdown.h1": Style(color=STYLE_EMPH, bold=True),
    "markdown.h2": Style(color=STYLE_EMPH, bold=True),
    "markdown.h3": Style(color=STYLE_EMPH, bold=True, italic=True),
    "markdown.h4": Style(color=COLOR_EXTRA, bold=True),
    "markdown.h5": Style(color=COLOR_EXTRA, italic=True),
    "markdown.h6": Style(color=COLOR_EXTRA, italic=True),
    "markdown.h7": Style(color=COLOR_EXTRA, italic=True, dim=True),
    "kash.warn": Style(color=COLOR_WARN, bold=True),
    "kash.error": Style(color=COLOR_ERROR, bold=True),
    "kash.ellipsis": Style(color=COLOR_HINT),
    "kash.at_mention": Style(color=COLOR_HINT, bold=True),
    "kash.indent": Style(color=COLOR_KEY, dim=True),
    "kash.str": Style(color=COLOR_LITERAL, italic=False, bold=False),
    # "kash.brace": Style(bold=True),  # Not required if the font is clear enough.
    "kash.comma": Style(bold=True),
    "kash.ipv4": Style(color=COLOR_KEY),
    "kash.ipv6": Style(color=COLOR_KEY),
    "kash.eui48": Style(color=COLOR_KEY),
    "kash.eui64": Style(color=COLOR_KEY),
    "kash.tag_start": Style(),
    "kash.tag_name": Style(color=COLOR_VALUE),
    "kash.tag_contents": Style(color="default"),
    "kash.tag_end": Style(),
    "kash.attrib_name": Style(color=COLOR_KEY, italic=False),
    "kash.attrib_equal": Style(),
    "kash.attrib_value": Style(color=COLOR_VALUE, italic=False),
    # "kash.number": Style(color=COLOR_KEY, italic=False),
    "kash.duration": Style(color=COLOR_KEY, italic=False),
    "kash.item_id_prefix": Style(color=COLOR_HINT, italic=False),
    "kash.part_count": Style(italic=True),
    "kash.time_ago": Style(color=COLOR_KEY, italic=False),
    "kash.file_size": Style(color=COLOR_VALUE, italic=False),
    "kash.code_span": Style(color=COLOR_VALUE, italic=False),
    # "kash.number_complex": Style(color=COLOR_KEY, italic=False),  # same
    "kash.bool_true": Style(color=COLOR_VALUE, italic=True),
    "kash.bool_false": Style(color=COLOR_VALUE, italic=True),
    "kash.none": Style(color=COLOR_VALUE, italic=True),
    # Add bgcolor="black" or underline=True?
    "kash.url": Style(color=COLOR_VALUE, italic=False, bold=False),
    "kash.uuid": Style(color=COLOR_LITERAL, bold=False),
    "kash.call": Style(italic=True),
    "kash.path": Style(color=COLOR_PATH),
    "kash.age_sec": STYLE_SIZE6,
    "kash.age_min": STYLE_SIZE5,
    "kash.age_hr": STYLE_SIZE4,
    "kash.age_day": STYLE_SIZE3,
    "kash.age_week": STYLE_SIZE2,
    "kash.age_year": STYLE_SIZE1,
    "kash.size_b": STYLE_SIZE1,
    "kash.size_k": STYLE_SIZE2,
    "kash.size_m": STYLE_SIZE3,
    "kash.size_gtp": STYLE_SIZE4,
    "kash.filename": Style(color=COLOR_VALUE),
    "kash.task_stack_header": Style(color=COLOR_TASK),
    "kash.task_stack": Style(color=COLOR_TASK),
    "kash.task_stack_prefix": Style(color=COLOR_HINT),
    # Emoji colors:
    "kash.task": Style(color=COLOR_TASK),
    "kash.success": Style(color=COLOR_SUCCESS, bold=True),
    "kash.skip": Style(color=COLOR_SKIP, bold=True),
    "kash.failure": Style(color=COLOR_ERROR, bold=True),
    "kash.timing": Style(color=COLOR_TIMING),
    "kash.saved": Style(color=COLOR_SAVED, bold=True),
    "kash.log_call": Style(color=COLOR_CALL, bold=True),
    "kash.box_chars": Style(color=COLOR_HINT),
}

## Boxes

HRULE_CHAR = "─"
VRULE_CHAR = "│"

UL_CORNER = "┌"
LL_CORNER = "└"
UR_CORNER = "┐"
LR_CORNER = "┘"


## Symbols

SYMBOL_SEP = "⎪"


## Symbols and emojis

PROMPT_MAIN = "❯"

PROMPT_FORM = "❯❯"

PROMPT_ASSIST = "(assistant) ❯"

EMOJI_HINT = "👉"

# More ideas: ⦿⧁⧀⦿⦾⟐⦊⟡


EMOJI_COMMAND = "⧁"

EMOJI_ACTION = "⛭"

EMOJI_SNIPPET = "❯"

EMOJI_HELP = "?"

EMOJI_SHELL = "⦊"

EMOJI_RECOMMENDED = "•"

EMOJI_WARN = "∆"

EMOJI_ERROR = "‼︎"

EMOJI_SAVED = "⩣"

EMOJI_TIMING = "⏱"

EMOJI_SUCCESS = "[✔︎]"

EMOJI_SKIP = "[∕]"

EMOJI_FAILURE = "[✘]"

EMOJI_CALL_BEGIN = "≫"

EMOJI_CALL_END = "≪"

EMOJI_ASSISTANT = "🤖"

EMOJI_MSG_INDENT = "⋮"

EMOJI_BREADCRUMB_SEP = "›"

EMOJI_TRUE = "✔︎"

EMOJI_FALSE = "✘"


def success_emoji(value: bool, success_only: bool = False) -> str:
    return EMOJI_TRUE if value else " " if success_only else EMOJI_FALSE


def format_success_emoji(value: bool, success_only: bool = False) -> Text:
    return Text(success_emoji(value, success_only), style=COLOR_SUCCESS if value else COLOR_FAILURE)


## Special headings

TASK_STACK_HEADER = "Task stack:"


## Rich setup


URL_CHARS = r"-0-9a-zA-Z$_+!`(),.?/;:&=%#~"

ITEM_ID_CHARS = URL_CHARS + r"@\[\]"


class KashHighlighter(RegexHighlighter):
    """
    Highlighter based on the repr highlighter with additions.
    """

    base_style = "kash."
    highlights = [
        _combine_regex(
            # Task stack in logs:
            f"(?P<task_stack_header>{re.escape(TASK_STACK_HEADER)})",
            f"(?P<task_stack>{re.escape(EMOJI_BREADCRUMB_SEP)}.*)",
            f"(?P<task_stack_prefix>{re.escape(EMOJI_MSG_INDENT)})",
            # Emojis that color the whole line:
            f"(?P<timing>{re.escape(EMOJI_TIMING)}.*)",
            # Color emojis by themselves:
            f"(?P<saved>{re.escape(EMOJI_SAVED)})",
            f"(?P<task>{re.escape(EMOJI_ACTION)})",
            f"(?P<success>{re.escape(EMOJI_SUCCESS)})",
            f"(?P<skip>{re.escape(EMOJI_SKIP)})",
            f"(?P<failure>{re.escape(EMOJI_FAILURE)})",
            f"(?P<warn>{re.escape(EMOJI_WARN)})",
            f"(?P<error>{re.escape(EMOJI_ERROR)})",
            f"(?P<log_call>{re.escape(EMOJI_CALL_BEGIN)}|{re.escape(EMOJI_CALL_END)})",
            f"(?P<box_chars>{HRULE_CHAR}|{VRULE_CHAR}|{UL_CORNER}|{LL_CORNER}|{UR_CORNER}|{LR_CORNER})",
        ),
        _combine_regex(
            # Quantities and times:
            r"\b(?P<age_sec>[0-9.,]+ ?(s|sec) ago)\b",
            r"\b(?P<age_min>[0-9.,]+ ?(m|min) ago)\b",
            r"\b(?P<age_hr>[0-9.,]+ ?(?:h|hr|hrs|hour|hours) ago)\b",
            r"\b(?P<age_day>[0-9.,]+ ?(?:d|day|days) ago)\b",
            r"\b(?P<age_week>[0-9.,]+ ?(?:w|week|weeks) ago)\b",
            r"\b(?P<age_year>[0-9.,]+ ?(?:y|year|years) ago)\b",
            r"\b(?P<size_b>(?<!\w)[0-9.,]+ ?(B|Bytes|bytes))\b",
            r"\b(?P<size_k>(?<!\w)[0-9.,]+ ?(K|KB|kb))\b",
            r"\b(?P<size_m>(?<!\w)[0-9.,]+ ?(M|MB|mb)\b)",
            r"\b(?P<size_gtp>(?<!\w)[0-9.,]+ ?(G|GB|gb|T|TB|tb|P|PB|pb))\b",
            r"\b(?P<part_count>\w+ \d+ of \d+(?!\-\w))\b",
            r"\b(?P<duration>(?<!\w)\-?[0-9]+\.?[0-9]*(ms|s)\b(?!\-\w))\b",
        ),
        _combine_regex(
            rf"\b(?P<item_id_prefix>id:\w+:[{ITEM_ID_CHARS}]+)",
            r"(?P<tag_start><)(?P<tag_name>[-\w.:|]*)(?P<tag_contents>[\w\W]*)(?P<tag_end>>)",
            r'(?P<attrib_name>[\w_-]{1,50})=(?P<attrib_value>"?[\w_]+"?)?',
            r"(?P<brace>[][{}()])",
        ),
        _combine_regex(
            r"(?P<ellipsis>(\.\.\.|…))",
            r"(?P<at_mention>(?<!\w)@(?=\w))",  # @some/file.txt
            # A subset of the repr-style highlights:
            r"(?P<ipv4>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            r"(?P<uuid>[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
            r"(?P<call>[\w.]*?)\(",
            r"\b(?P<bool_true>True)\b|\b(?P<bool_false>False)\b|\b(?P<none>None)\b",
            # r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b(?!\-\w)|0x[0-9a-fA-F]*)",
            r"(?P<path>\B((~[-\w._+]*)?/[-\w._+]+)*\/)(?P<filename>[-\w._+]*)?",
            # r"(?P<relpath>\B([\w._+][-\w._+~]*)*(/\w[-\w._+]*)+)*\.(html|htm|pdf|yaml|yml|md|txt)",
            r"(?<![\\\w])(?P<str>b?'''.*?(?<!\\)'''|b?'.*?(?<!\\)'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
            rf"(?P<url>(file|https|http|ws|wss)://[{URL_CHARS}]*)",
            r"(?P<code_span>`[^`\n]+`)",
        ),
    ]


## Other formatting functions

AGO_SUFFIX = " ago"


def color_for_qty(size_str: str) -> Style | None:
    # Size patterns
    if re.search(r"[0-9.,]+ ?(B|Bytes|bytes)", size_str):
        return STYLE_SIZE1
    if re.search(r"[0-9.,]+ ?(K|KB|kb)", size_str):
        return STYLE_SIZE2
    if re.search(r"[0-9.,]+ ?(M|MB|mb)", size_str):
        return STYLE_SIZE3
    if re.search(r"[0-9.,]+ ?(G|GB|gb|T|TB|tb|P|PB|pb)", size_str):
        return STYLE_SIZE4

    # Age patterns
    if re.search(r"[0-9.,]+ ?(s|sec)" + AGO_SUFFIX, size_str):
        return STYLE_SIZE6
    if re.search(r"[0-9.,]+ ?(m|min)" + AGO_SUFFIX, size_str):
        return STYLE_SIZE5
    if re.search(r"[0-9.,]+ ?(?:h|hr|hrs|hour|hours)" + AGO_SUFFIX, size_str):
        return STYLE_SIZE4
    if re.search(r"[0-9.,]+ ?(?:d|day|days)" + AGO_SUFFIX, size_str):
        return STYLE_SIZE3
    if re.search(r"[0-9.,]+ ?(?:w|week|weeks)" + AGO_SUFFIX, size_str):
        return STYLE_SIZE2
    if re.search(r"[0-9.,]+ ?(?:y|year|years)" + AGO_SUFFIX, size_str):
        return STYLE_SIZE1

    return None


def colorize_qty(text: Text) -> Text:
    """
    Colorize the quantity portion of a string in place. For age patterns, doesn't
    colorize the "ago" part.
    """
    style = color_for_qty(text.plain)
    if style:
        qty_len = len(text.plain)
        if text.plain.endswith(AGO_SUFFIX):
            qty_len -= len(AGO_SUFFIX)

        text.stylize(style, start=0, end=qty_len)
        if qty_len < len(text.plain):
            text.stylize(STYLE_HINT, start=qty_len, end=len(text.plain))

    return text
