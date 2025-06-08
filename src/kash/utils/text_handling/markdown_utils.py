import re
from pathlib import Path
from textwrap import dedent
from typing import Any, TypeAlias

import marko
import regex
from marko.block import Heading, ListItem
from marko.inline import Link

from kash.utils.common.url import Url

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


def extract_links(content: str, include_internal=False) -> list[str]:
    """
    Extract all links from Markdown content.

    Raises:
        marko.ParseError: If the markdown content contains invalid syntax that cannot be parsed.
    """
    document = marko.parse(content)
    return _tree_links(document, include_internal)


def extract_file_links(file_path: Path, include_internal=False) -> list[str]:
    """
    Extract all links from a Markdown file. Future: Include textual and section context.

    Returns an empty list if there are parsing errors.
    """
    import logging

    try:
        content = file_path.read_text()
        return extract_links(content, include_internal)
    except Exception as e:
        logging.warning(f"Failed to extract links from {file_path}: {e}")
        return []


def extract_first_header(content: str) -> str | None:
    """
    Extract the first header from markdown content if present.
    Also drops any formatting, so the result can be used as a document title.

    Raises:
        marko.ParseError: If the markdown content contains invalid syntax that cannot be parsed.
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


def _extract_list_item_text(element: Any) -> str:
    """
    Extract text from a list item, excluding nested lists.
    """
    from marko.block import List
    from marko.inline import CodeSpan

    if isinstance(element, str):
        return element
    elif isinstance(element, List):
        # Skip nested lists
        return ""
    elif isinstance(element, CodeSpan):
        # Handle inline code spans - preserve backticks
        return f"`{''.join(_extract_list_item_text(child) for child in element.children)}`"
    elif hasattr(element, "children"):
        return "".join(_extract_list_item_text(child) for child in element.children)
    else:
        return ""


def _tree_bullet_points(element: marko.block.Document) -> list[str]:
    bullet_points: list[str] = []

    def _find_bullet_points(element):
        if isinstance(element, ListItem):
            # Extract text from this list item, excluding nested lists
            bullet_points.append(_extract_list_item_text(element).strip())
            # Then recursively process any nested lists within this item
            if hasattr(element, "children"):
                for child in element.children:
                    _find_bullet_points(child)
        elif hasattr(element, "children"):
            for child in element.children:
                _find_bullet_points(child)

    _find_bullet_points(element)
    return bullet_points


def extract_bullet_points(content: str, *, strict: bool = False) -> list[str]:
    """
    Extract list item values from a Markdown file.

    If no bullet points are found and `strict` is False, returns the entire content
    as a single item (treating plain text as if it were the first bullet point).
    If `strict` is True, only actual list items are returned.

    Raises:
        ValueError: If `strict` is True and no bullet points are found.
        marko.ParseError: If the markdown content contains invalid syntax that cannot be parsed.
    """

    document = marko.parse(content)
    bullet_points = _tree_bullet_points(document)

    # If no bullet points found
    if not bullet_points:
        if strict:
            raise ValueError("No bullet points found in content")
        elif content.strip():
            # Not strict mode, treat as plain text
            return [content.strip()]

    return bullet_points


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

    Raises:
        marko.ParseError: If the markdown content contains invalid syntax that cannot be parsed.
        ValueError: If a heading with an unsupported level is encountered.
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

    Raises:
        marko.ParseError: If the markdown content contains invalid syntax that cannot be parsed.
        ValueError: If a heading with an unsupported level is encountered.
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


def test_extract_bullet_points() -> None:
    # Empty content
    assert extract_bullet_points("") == []

    # No lists (strict mode)
    try:
        extract_bullet_points("Just some text without lists.", strict=True)
        raise AssertionError("Expected ValueError for strict mode with no bullet points")
    except ValueError as e:
        assert "No bullet points found" in str(e)
    # No lists (non-strict mode - should return as single item)
    assert extract_bullet_points("Just some text without lists.") == [
        "Just some text without lists."
    ]

    # Simple unordered list
    content = """
- First item
- Second item
- Third item
"""
    expected = ["First item", "Second item", "Third item"]
    assert extract_bullet_points(content) == expected

    # Simple ordered list
    content = """
1. First item
2. Second item
3. Third item
"""
    expected = ["First item", "Second item", "Third item"]
    assert extract_bullet_points(content) == expected

    # Mixed list types (asterisk and dash)
    content = """
* Item with asterisk
- Item with dash
+ Item with plus
"""
    expected = ["Item with asterisk", "Item with dash", "Item with plus"]
    assert extract_bullet_points(content) == expected

    # List items with formatting
    content = """
- **Bold item**
- *Italic item*
- `Code item`
- [Link item](http://example.com)
- Item with _multiple_ **formats** and `code`
"""
    expected = [
        "Bold item",
        "Italic item",
        "`Code item`",
        "Link item",
        "Item with multiple formats and `code`",
    ]
    assert extract_bullet_points(content) == expected

    # Nested lists
    content = """
- Top level item 1
  - Nested item 1.1
  - Nested item 1.2
- Top level item 2
  1. Nested ordered 2.1
  2. Nested ordered 2.2
"""
    expected = [
        "Top level item 1",
        "Nested item 1.1",
        "Nested item 1.2",
        "Top level item 2",
        "Nested ordered 2.1",
        "Nested ordered 2.2",
    ]
    assert extract_bullet_points(content) == expected

    # Multi-line list items
    content = """
- First item that spans
  multiple lines with content
- Second item
  that also spans multiple
  lines
"""
    expected = [
        "First item that spans\nmultiple lines with content",
        "Second item\nthat also spans multiple\nlines",
    ]
    assert extract_bullet_points(content) == expected

    # Lists mixed with other content
    content = """
# Header

Some text before the list.

- First item
- Second item

More text after the list.

1. Another list item
2. Final item

Conclusion text.
"""
    expected = ["First item", "Second item", "Another list item", "Final item"]
    assert extract_bullet_points(content) == expected

    # List items with complex content
    content = """
- Item with **bold** and *italic* and `inline code`
- Item with [external link](https://example.com) and [internal link](#section)
- Item with line breaks
  and continued text
"""
    expected = [
        "Item with bold and italic and `inline code`",
        "Item with external link and internal link",
        "Item with line breaks\nand continued text",
    ]
    assert extract_bullet_points(content) == expected

    # Edge case: empty list items
    content = """
- 
- Non-empty item
-   
"""
    expected = ["", "Non-empty item", ""]
    assert extract_bullet_points(content) == expected

    # Plain text handling (default behavior - not strict)
    plain_text = "This is just plain text without any lists."
    expected = ["This is just plain text without any lists."]
    assert extract_bullet_points(plain_text) == expected
    assert extract_bullet_points(plain_text, strict=False) == expected

    # Plain text handling (strict mode)
    try:
        extract_bullet_points(plain_text, strict=True)
        raise AssertionError("Expected ValueError for strict mode with no bullet points")
    except ValueError as e:
        assert "No bullet points found" in str(e)

    # Multi-line plain text handling
    multiline_plain = """This is a paragraph
with multiple lines
and no bullets."""
    expected_multiline = ["This is a paragraph\nwith multiple lines\nand no bullets."]
    assert extract_bullet_points(multiline_plain) == expected_multiline
    try:
        extract_bullet_points(multiline_plain, strict=True)
        raise AssertionError("Expected ValueError for strict mode with no bullet points")
    except ValueError as e:
        assert "No bullet points found" in str(e)

    # Mixed content with no lists in strict mode
    mixed_no_lists = """
# Header
Some text here.
**Bold text** and *italic*.
"""
    try:
        extract_bullet_points(mixed_no_lists, strict=True)
        raise AssertionError("Expected ValueError for strict mode with no bullet points")
    except ValueError as e:
        assert "No bullet points found" in str(e)
    # Non-strict should return the content as single item
    assert len(extract_bullet_points(mixed_no_lists, strict=False)) == 1


def test_markdown_utils_exceptions() -> None:
    """Test exception handling for markdown utility functions."""
    import tempfile

    # Test extract_file_links with non-existent file
    result = extract_file_links(Path("/non/existent/file.md"))
    assert result == []  # Should return empty list for any error

    # Test extract_file_links with empty file (should work fine)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
        tmp.write("")
        tmp_path = Path(tmp.name)

    try:
        result = extract_file_links(tmp_path)
        assert result == []  # Empty file has no links
    finally:
        tmp_path.unlink()

    # Test with invalid markdown formatting (markdown is very permissive)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
        tmp.write("[incomplete link\n# Header\n- List item")
        tmp_path = Path(tmp.name)

    try:
        result = extract_file_links(tmp_path)
        # Should still work - marko is very permissive with markdown
        assert isinstance(result, list)
    finally:
        tmp_path.unlink()

    # Test extract_links with string content
    content = "Check out [this link](https://example.com) and [internal](#section)"
    result = extract_links(content)
    assert "https://example.com" in result
    assert "#section" not in result  # Internal links excluded by default

    result_with_internal = extract_links(content, include_internal=True)
    assert "https://example.com" in result_with_internal
    assert "#section" in result_with_internal
