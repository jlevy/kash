import re
from textwrap import dedent
from typing import Any, TypeAlias

import marko
import regex
from marko.block import Heading, ListItem
from marko.inline import Link

from kash.config.logger import get_logger
from kash.utils.common.url import Url

log = get_logger(__name__)

HTag: TypeAlias = str

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


def extract_first_header(content: str) -> str | None:
    """
    Extract the first header from markdown content if present.
    Also drops any formatting, so the result can be used as a document title.
    """
    document = marko.parse(content)

    if document.children and isinstance(document.children[0], Heading):
        return _extract_text(document.children[0]).strip()

    return None


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


def _type_from_heading(heading: Heading) -> HTag:
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


def extract_headings(text: str) -> list[tuple[HTag, str]]:
    """
    Extract all Markdown headings from the given content.
    Returns a list of (tag, text) tuples:
    [("h1", "Main Title"), ("h2", "Subtitle")]
    where `#` corresponds to `h1`, `##` to `h2`, etc.
    """
    document = marko.parse(text)
    headings_list: list[tuple[HTag, str]] = []

    def _collect_headings_recursive(element: Any) -> None:
        if isinstance(element, Heading):
            tag = _type_from_heading(element)
            content = _extract_text(element).strip()
            headings_list.append((tag, content))

        if hasattr(element, "children"):
            for child in element.children:
                _collect_headings_recursive(child)

    _collect_headings_recursive(document)

    return headings_list


def first_heading(text: str, *, allowed_tags: tuple[HTag, ...] = ("h1", "h2")) -> str | None:
    """
    Find the text of the first heading. Returns first h1 if present, otherwise first h2, etc.
    """
    headings = extract_headings(text)
    for goal_tag in allowed_tags:
        for h_tag, h_text in headings:
            if h_tag == goal_tag:
                return h_text
    return None


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


def test_extract_first_header() -> None:
    assert extract_first_header("# Header 1") == "Header 1"
    assert extract_first_header("Not a header\n# Header later") is None
    assert extract_first_header("") is None
    assert (
        extract_first_header("## *Formatted* _Header_ [link](#anchor)") == "Formatted Header link"
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


def test_extract_headings_and_first_header() -> None:
    markdown_content = dedent("""
        # Title 1
        Some text.
        ## Subtitle 1.1
        More text.
        ### Sub-subtitle 1.1.1
        Even more text.
        # Title 2 *with formatting*
        And final text.
        ## Subtitle 2.1
        """)
    expected_headings = [
        ("h1", "Title 1"),
        ("h2", "Subtitle 1.1"),
        ("h3", "Sub-subtitle 1.1.1"),
        ("h1", "Title 2 with formatting"),
        ("h2", "Subtitle 2.1"),
    ]
    assert extract_headings(markdown_content) == expected_headings

    assert first_heading(markdown_content) == "Title 1"
    assert first_heading(markdown_content) == "Title 1"
    assert first_heading(markdown_content, allowed_tags=("h2",)) == "Subtitle 1.1"
    assert first_heading(markdown_content, allowed_tags=("h3",)) == "Sub-subtitle 1.1.1"
    assert first_heading(markdown_content, allowed_tags=("h4",)) is None

    assert extract_headings("") == []
    assert first_heading("") is None
    assert first_heading("Just text, no headers.") is None

    markdown_h2_only = "## Only H2 Here"
    assert extract_headings(markdown_h2_only) == [("h2", "Only H2 Here")]
    assert first_heading(markdown_h2_only) == "Only H2 Here"
    assert first_heading(markdown_h2_only, allowed_tags=("h2",)) == "Only H2 Here"

    formatted_header_md = "## *Formatted* _Header_ [link](#anchor)"
    assert extract_headings(formatted_header_md) == [("h2", "Formatted Header link")]
    assert first_heading(formatted_header_md, allowed_tags=("h2",)) == "Formatted Header link"
