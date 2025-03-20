import re

from rich.text import Text

from kash.config.logger import get_logger
from kash.config.settings import global_settings
from kash.config.text_styles import COLOR_COMMENT, STYLE_CODE
from kash.shell.output.kerm_codes import KriLink, TextTooltip, UIAction, UIActionType

log = get_logger(__name__)


def text_with_tooltip(text: str, hover_text: str = "Click to paste") -> KriLink:
    return KriLink.with_attrs(
        link_text=text,
        hover=TextTooltip(text=hover_text),
    )


_comment_char_regex = re.compile(r"^\s*(#|//|/\*)")


def is_comment(line: str) -> bool:
    return _comment_char_regex.match(line) is not None


def click_to_paste(text: str, hover_text: str = "Click to paste") -> Text:
    """
    Make a bit of text or code clickable. Use on filenames, commands, etc.
    Requires Kerm code support.
    """
    kerm_codes_enabled = global_settings().use_kerm_codes

    if kerm_codes_enabled:
        link = KriLink.with_attrs(
            link_text=text,
            hover=TextTooltip(text=hover_text),
            click=UIAction(action_type=UIActionType.paste_text),
        )
        return Text.from_ansi(link.as_osc8(), style=STYLE_CODE)
    else:
        return Text(text, style=STYLE_CODE)


def clickable_script_block(code: str) -> Text:
    """
    Insert Kerm links into a code block, skipping comments and making
    each line of code clickable.
    """

    lines: list[str] = code.splitlines()
    texts: list[Text] = []
    for line in lines:
        if is_comment(line):
            texts.append(Text(line, style=COLOR_COMMENT))
        else:
            texts.append(click_to_paste(line))

    return Text("\n").join(texts)
