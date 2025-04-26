import re
from typing import Any

import marko
import regex
from marko.block import Heading, ListItem
from marko.inline import Link

from kash.config.logger import get_logger
from kash.utils.common.url import Url

log = get_logger(__name__)

# Characters that commonly need escaping in Markdown inline text.
MARKDOWN_ESCAPE_CHARS = r"([\\`*_{}\[\]()#+.!-])"
MARKDOWN_ESCAPE_RE = re.compile(MARKDOWN_ESCAPE_CHARS)


def escape_markdown(text: str) -> str:
    """
    Escape characters with special meaning in Markdown.
    """
    return MARKDOWN_ESCAPE_RE.sub(r"\\\1", text)


def as_bullet_points(values: list[Any]) -> str:
    """
    Convert a list of values to a Markdown bullet-point list. If a value is a string,
    it is treated like Markdown. If it's something else it's converted to a string
    and also escaped for Markdown.
    """
    points: list[str] = []
    for value in values:
        value = value.replace("\n", " ").strip()
        if isinstance(value, str):
            points.append(value)
        else:
            points.append(escape_markdown(str(value)))

    return "\n\n".join(f"- {point}" for point in points)


def markdown_link(text: str, url: str | Url) -> str:
    """
    Create a Markdown link.
    """
    text = text.replace("[", "\\[").replace("]", "\\]")
    return f"[{text}]({url})"


def is_markdown_header(markdown: str) -> bool:
    """
    Is the start of this content a Markdown header?
    """
    return regex.match(r"^#+ ", markdown) is not None


def _tree_links(element, include_internal=False):
    links = []

    def _find_links(element):
        match element:
            case Link():
                if include_internal or not element.dest.startswith("#"):
                    links.append(element.dest)
            case _:
                if hasattr(element, "children"):
                    for child in element.children:
                        _find_links(child)

    _find_links(element)
    return links


def extract_links(file_path: str, include_internal=False) -> list[str]:
    """
    Extract all links from a Markdown file. Future: Include textual and section context.
    """

    with open(file_path) as file:
        content = file.read()
        document = marko.parse(content)
        return _tree_links(document, include_internal)


def _extract_text(element: Any) -> str:
    if isinstance(element, str):
        return element
    elif hasattr(element, "children"):
        return "".join(_extract_text(child) for child in element.children)
    else:
        return ""


def _tree_bullet_points(element: marko.block.Document) -> list[str]:
    bullet_points: list[str] = []

    def _find_bullet_points(element):
        if isinstance(element, ListItem):
            bullet_points.append(_extract_text(element).strip())
        elif hasattr(element, "children"):
            for child in element.children:
                _find_bullet_points(child)

    _find_bullet_points(element)
    return bullet_points


def extract_bullet_points(content: str) -> list[str]:
    """
    Extract list item values from a Markdown file.
    """

    document = marko.parse(content)
    return _tree_bullet_points(document)


def _type_from_heading(heading: Heading) -> str:
    if heading.level in [1, 2, 3, 4, 5, 6]:
        return f"h{heading.level}"
    else:
        raise ValueError(f"Unsupported heading: {heading}: level {heading.level}")


def _last_unescaped_bracket(text: str, index: int) -> str | None:
    escaped = False
    for i in range(index - 1, -1, -1):
        ch = text[i]
        if ch == "\\":
            escaped = not escaped  # Toggle escaping chain
            continue
        if ch in "[]":
            if not escaped:
                return ch
        # Reset escape status after any non‑backslash char
        escaped = False
    return None


def find_markdown_text(
    pattern: re.Pattern[str], text: str, *, start_pos: int = 0
) -> re.Match[str] | None:
    """
    Return first regex `pattern` match in `text` not inside an existing link.

    A match is considered inside a link when the most recent unescaped square
    bracket preceding the match start is an opening bracket "[".
    """

    pos = start_pos
    while True:
        match = pattern.search(text, pos)
        if match is None:
            return None

        last_bracket = _last_unescaped_bracket(text, match.start())
        if last_bracket != "[":
            return match

        # Skip this match and continue searching
        pos = match.end()


## Tests


def test_escape_markdown() -> None:
    assert escape_markdown("") == ""
    assert escape_markdown("Hello world") == "Hello world"
    assert escape_markdown("`code`") == "\\`code\\`"
    assert escape_markdown("*italic*") == "\\*italic\\*"
    assert escape_markdown("_bold_") == "\\_bold\\_"
    assert escape_markdown("{braces}") == "\\{braces\\}"
    assert escape_markdown("# header") == "\\# header"
    assert escape_markdown("1. item") == "1\\. item"
    assert escape_markdown("line+break") == "line\\+break"
    assert escape_markdown("dash-") == "dash\\-"
    assert escape_markdown("!bang") == "\\!bang"
    assert escape_markdown("backslash\\") == "backslash\\\\"
    assert escape_markdown("Multiple *special* chars [here](#anchor).") == (
        "Multiple \\*special\\* chars \\[here\\]\\(\\#anchor\\)\\."
    )


def test_find_markdown_text() -> None:  # pragma: no cover
    # Match is returned when the term is not inside a link.
    text = "Foo bar baz"
    pattern = re.compile("Foo Bar", re.IGNORECASE)
    match = find_markdown_text(pattern, text)
    assert match is not None and match.group(0) == "Foo bar"

    # Skips occurrence inside link and returns the first one outside.
    text = "[Foo](http://example.com) something Foo"
    pattern = re.compile("Foo", re.IGNORECASE)
    match = find_markdown_text(pattern, text)
    assert match is not None
    assert match.start() > text.index(") ")
    assert text[match.start() : match.end()] == "Foo"

    # Returns None when the only occurrences are inside links.
    text = "prefix [bar](http://example.com) suffix"
    pattern = re.compile("bar", re.IGNORECASE)
    match = find_markdown_text(pattern, text)
    assert match is None
