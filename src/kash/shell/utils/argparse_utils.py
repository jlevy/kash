from typing import Any

from rich import get_console
from rich_argparse.contrib import ParagraphRichHelpFormatter

MAX_WIDTH = 88
MIN_WIDTH = 40


class WrappedColorFormatter(ParagraphRichHelpFormatter):
    """
    A formatter for argparse that colorizes with rich_argparse and also wraps
    text to console width, which is better for readability in both wide and
    narrow consoles. Also preserves paragraphs, unlike the default argparse
    formatters.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        width = max(MIN_WIDTH, min(MAX_WIDTH, get_console().width))
        super().__init__(*args, width=width, **kwargs)
