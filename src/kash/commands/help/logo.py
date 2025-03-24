import re
from pathlib import Path

from rich.box import SQUARE
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from kash.config.colors import rich_terminal_dark
from kash.config.logger import get_logger, record_console
from kash.config.text_styles import (
    COLOR_HINT,
    CONSOLE_WRAP_WIDTH,
    LOGO_LARGE,
    LOGO_SPACER,
    STYLE_EMPH,
    STYLE_LOGO,
    TAGLINE_STYLED,
)
from kash.exec import kash_command
from kash.shell.output.shell_output import cprint

log = get_logger(__name__)


# Break the line into non-space and space chunks by using a regex.
# Colorize each chunk and optionally swap lines to spaces.
def logo_colorize_line(line: str, space_replacement: str = " ", line_offset: int = 0) -> Text:
    line = " " * line_offset + line
    # bits = re.findall(r"[^\s]+|\s+", line)
    bits = line
    texts = []
    solid_count = 0
    for i, bit in enumerate(bits):
        if bit.strip():
            bright_color = i > line_offset + 5 and bit not in "░"
            texts.append(
                Text(
                    bit,
                    style=STYLE_LOGO if bright_color else STYLE_EMPH,
                )
            )
            solid_count += 1
        else:
            bit = re.sub(r" ", space_replacement, bit)
            if i > 0:
                bit = " " + bit[1:]
            if i < len(bits) - 1:
                bit = bit[:-1] + " "
            texts.append(Text(bit, style=COLOR_HINT))
    return Text.assemble(*texts)


def color_logo() -> Group:
    logo_lines = LOGO_LARGE.split("\n")
    left_margin = 2
    offset = 0
    return Group(
        "",
        *[logo_colorize_line(line, " ", left_margin + offset) for line in logo_lines],
        Text.assemble(" " * left_margin, TAGLINE_STYLED),
    )


def branded_box(content: Group | None, version: str | None = None) -> Panel:
    panel_width = CONSOLE_WRAP_WIDTH

    logo_lines = LOGO_LARGE.split("\n")
    rest_offset = (panel_width - 4 - len(logo_lines[0])) // 2
    tagline_offset = (panel_width - 4 - len(TAGLINE_STYLED)) // 2

    colored_lines = [logo_colorize_line(line, " ", rest_offset) for line in logo_lines]
    header = None
    if version:
        footer = Text(version, style=COLOR_HINT, justify="right")
    else:
        footer = None

    body = ["", content] if content else []

    return Panel(
        Group(
            Text.assemble(" " * tagline_offset, LOGO_SPACER),
            *colored_lines,
            Text.assemble(" " * tagline_offset, TAGLINE_STYLED),
            *body,
        ),
        title=header,
        title_align="center",
        subtitle=footer,
        subtitle_align="right",
        border_style=COLOR_HINT,
        padding=(0, 1),
        width=panel_width,
        box=SQUARE,
    )


@kash_command
def kash_logo(box: bool = False, svg_out: str | None = None, html_out: str | None = None) -> None:
    """
    Show the kash logo.
    """
    logo = branded_box(None) if box else color_logo()

    cprint(logo)

    if svg_out:
        with record_console() as console:
            console.print(logo)
        with Path(svg_out).open("w") as f:
            f.write(console.export_svg(theme=rich_terminal_dark))
        log.message(f"Wrote logo: {svg_out}")
    if html_out:
        with record_console() as console:
            console.print(logo)
        with Path(html_out).open("w") as f:
            f.write(console.export_html(theme=rich_terminal_dark))
        log.message(f"Wrote logo: {html_out}")
