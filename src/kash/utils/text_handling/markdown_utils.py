import re
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent
from typing import Any, TypeAlias

import regex
from chopdiff.html import rewrite_html_img_urls
from flowmark import flowmark_markdown, line_wrap_by_sentence
from marko.block import Heading, LinkRefDef, ListItem
from marko.inline import AutoLink, Image, Link

from kash.utils.common.url import Url

HTag: TypeAlias = str


UrlRewriter: TypeAlias = Callable[[str], str | None]
"""
An URL rewriter function takes a URL string and returns a new URL or
None to skip rewriting.
"""

# Characters that commonly need escaping in Markdown inline text.
MARKDOWN_ESCAPE_CHARS = r"([\\`*_{}\[\]()#+.!-])"
MARKDOWN_ESCAPE_RE = re.compile(MARKDOWN_ESCAPE_CHARS)

# Use flowmark for Markdown parsing and rendering.
# This replaces the single shared Markdown object that marko offers.
MARKDOWN = flowmark_markdown(line_wrap_by_sentence(is_markdown=True))


# Regex for a markdown footnote definition line: "[^id]: ..."
FOOTNOTE_DEF_RE = re.compile(r"^\[\^[^\]]+\]:")


def normalize_footnotes_in_markdown(content: str) -> str:
    """
    Ensure blank lines between consecutive footnote definitions.

    Some markdown parsers (marko) merge consecutive footnotes without blank
    lines into a single definition. This adds blank lines where needed.
    """
    lines = content.split("\n")
    result: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        result.append(line)

        # Check if this is a footnote definition
        if FOOTNOTE_DEF_RE.match(line):
            # Look ahead to see if the next non-empty line is also a footnote
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                result.append(lines[j])
                j += 1

            if j < len(lines) and FOOTNOTE_DEF_RE.match(lines[j]):
                # Next non-empty line is also a footnote, add blank line
                result.append("")

            i = j
        else:
            i += 1

    return "\n".join(result)


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


def comprehensive_transform_tree(element: Any, transformer: Callable[[Any], None]) -> None:
    """
    Enhanced tree traversal that handles all marko element types including GFM tables.

    This extends flowmark's transform_tree to handle table elements that are not
    included in flowmark's ContainerElement tuple.
    """
    transformer(element)

    # Handle all types that can contain children
    if hasattr(element, "children") and element.children is not None:
        if isinstance(element.children, list):
            # Create a copy for safe iteration if modification occurs
            current_children = list(element.children)
            for child in current_children:
                comprehensive_transform_tree(child, transformer)


def _tree_links(element, include_internal=False) -> list[str]:
    links: list[str] = []

    def _find_links(element):
        if isinstance(element, (Link, AutoLink)):
            if include_internal or not element.dest.startswith("#"):
                assert isinstance(element.dest, str)
                links.append(element.dest)

    comprehensive_transform_tree(element, _find_links)
    return links


# TODO: Marko seems to include trailing parentheses on bare links.
# Fix this in flowmark
def _fix_link(url: str) -> str:
    return url.rstrip(")")


def extract_urls(content: str, include_internal=False) -> list[Url]:
    """
    Extract all URLs from Markdown content. Deduplicates and preserves order.

    Raises:
        marko.ParseError: If the markdown content contains invalid syntax that cannot be parsed.
    """
    content = normalize_footnotes_in_markdown(content)
    document = MARKDOWN.parse(content)
    all_links = _tree_links(document, include_internal)

    # Deduplicate while preserving order
    seen: dict[str, None] = {}
    result: list[Url] = []
    for link in all_links:
        if link not in seen:
            seen[link] = None
            result.append(Url(_fix_link(link)))
    return result


def extract_file_urls(file_path: Path, include_internal=False) -> list[Url]:
    """
    Extract all URLs from a Markdown file. Future: Include textual and section context.

    Returns an empty list if there are parsing errors.
    """
    import logging

    try:
        content = file_path.read_text()
        return extract_urls(content, include_internal)
    except Exception as e:
        logging.warning(f"Failed to extract links from {file_path}: {e}")
        return []


def rewrite_urls(
    content: str,
    url_rewriter: UrlRewriter,
    element_types: tuple[type, ...] = (Image, Link, AutoLink, LinkRefDef),
) -> str:
    """
    Rewrite URLs in markdown content using the provided rewriter function.

    Args:
        content: The markdown content to process
        url_rewriter: A function of type UrlRewriter that takes a URL string and returns
                     a new URL string to replace it, or None to skip rewriting that URL
        element_types: Tuple of element types to process (default: all URL-containing types)

    Returns:
        The markdown content with rewritten URLs

    Raises:
        marko.ParseError: If the markdown content contains invalid syntax that cannot be parsed.
    """
    content = normalize_footnotes_in_markdown(content)
    document = MARKDOWN.parse(content)
    _rewrite_tree_urls(document, url_rewriter, element_types)

    return MARKDOWN.render(document)


def rewrite_image_urls(
    content: str, from_prefix: str, to_prefix: str, *, include_img_tags: bool = True
) -> str:
    """
    Rewrite image paths in markdown content by replacing matching prefixes.

    This works with URLs, relative paths, or absolute paths. Optionally also
    processes HTML img tags within the markdown content.

    Args:
        content: The markdown content to process
        from_prefix: The prefix to match and replace
        to_prefix: The prefix to replace the from_prefix with
        include_img_tags: If True, also rewrite src attributes in HTML img tags

    Returns:
        The markdown content with rewritten image paths

    Raises:
        marko.ParseError: If the markdown content contains invalid syntax that cannot be parsed.
    """

    def prefix_rewriter(url: str) -> str | None:
        if url.startswith(from_prefix):
            return url.replace(from_prefix, to_prefix, 1)
        return None  # Skip URLs that don't match the prefix

    # First rewrite markdown image syntax
    result = rewrite_urls(content, prefix_rewriter, element_types=(Image,))

    # Then optionally rewrite HTML img tags
    if include_img_tags:
        result = rewrite_html_img_urls(result, from_prefix=from_prefix, to_prefix=to_prefix)
    return result


def _rewrite_tree_urls(
    element: Any,
    url_rewriter: UrlRewriter,
    element_types: tuple[type, ...],
) -> None:
    """
    Recursively traverse the markdown AST and rewrite URLs in specified element types.
    """

    def _rewrite_url(element: Any) -> None:
        if isinstance(element, element_types) and hasattr(element, "dest"):
            url = element.dest
            new_url = url_rewriter(url)
            if new_url is not None:
                element.dest = new_url

    comprehensive_transform_tree(element, _rewrite_url)


def _is_remote_url(url: str) -> bool:
    """
    Check if a URL is a remote URL (starts with http:// or https://)
    """
    return url.startswith(("http://", "https://"))


def extract_first_header(content: str) -> str | None:
    """
    Extract the first header from markdown content if present.
    Also drops any formatting, so the result can be used as a document title.

    Raises:
        marko.ParseError: If the markdown content contains invalid syntax that cannot be parsed.
    """
    content = normalize_footnotes_in_markdown(content)
    document = MARKDOWN.parse(content)

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


def _extract_list_item_markdown(element: Any) -> str:
    """
    Extract markdown from a list item, preserving all formatting.
    """
    from marko.block import BlankLine, List, Paragraph
    from marko.inline import CodeSpan, Emphasis, Link, StrongEmphasis

    if isinstance(element, str):
        return element
    elif isinstance(element, List):
        # Skip nested lists
        return ""
    elif isinstance(element, BlankLine):
        # Preserve paragraph breaks
        return "\n\n"
    elif isinstance(element, Paragraph):
        # Extract content from paragraph
        return "".join(_extract_list_item_markdown(child) for child in element.children)
    elif isinstance(element, CodeSpan):
        return f"`{''.join(_extract_list_item_markdown(child) for child in element.children)}`"
    elif isinstance(element, Emphasis):
        return f"*{''.join(_extract_list_item_markdown(child) for child in element.children)}*"
    elif isinstance(element, StrongEmphasis):
        return f"**{''.join(_extract_list_item_markdown(child) for child in element.children)}**"
    elif isinstance(element, Link):
        text = "".join(_extract_list_item_markdown(child) for child in element.children)
        return f"[{text}]({element.dest})"
    elif hasattr(element, "children"):
        return "".join(_extract_list_item_markdown(child) for child in element.children)
    else:
        return ""


def extract_bullet_points(
    content: str, *, strict: bool = False, allow_paragraphs: bool = False
) -> list[str]:
    """
    Extract list item values from a Markdown file, preserving all original formatting.

    If no bullet points are found and `strict` is False, returns the entire content
    as a single item (treating plain text as if it were the first bullet point).

    If `strict` is True, only actual list items are returned.

    If `allow_paragraphs` is True, if the content contains multiple paragraphs and no
    bullet points are found, return the paragraphs as separate items.

    Raises:
        ValueError: If `strict` is True and no bullet points are found.
        marko.ParseError: If the markdown content contains invalid syntax that cannot be parsed.
    """
    content = normalize_footnotes_in_markdown(content)
    document = MARKDOWN.parse(content)
    bullet_points: list[str] = []

    def _collect_bullet_point(element):
        if isinstance(element, ListItem):
            # Extract markdown from this list item, preserving formatting
            bullet_points.append(_extract_list_item_markdown(element).strip())

    comprehensive_transform_tree(document, _collect_bullet_point)

    # If no bullet points found
    if not bullet_points:
        if strict:
            raise ValueError("No bullet points found in content")
        elif allow_paragraphs and "\n\n" in content:
            return [p.strip() for p in content.split("\n\n")]
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
    text = normalize_footnotes_in_markdown(text)
    document = MARKDOWN.parse(text)
    headings_list: list[tuple[HTag, str]] = []

    def _collect_heading(element: Any) -> None:
        if isinstance(element, Heading):
            tag = _type_from_heading(element)
            content = _extract_text(element).strip()
            headings_list.append((tag, content))

    comprehensive_transform_tree(document, _collect_heading)

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
    content = dedent("""
        - First item
        - Second item
        - Third item
        """)
    expected = ["First item", "Second item", "Third item"]
    assert extract_bullet_points(content) == expected

    # Simple ordered list
    content = dedent("""
        1. First item
        2. Second item
        3. Third item
        """)
    expected = ["First item", "Second item", "Third item"]
    assert extract_bullet_points(content) == expected

    # Mixed list types (asterisk and dash)
    content = dedent("""
        * Item with asterisk
        - Item with dash
        + Item with plus
        """)
    expected = ["Item with asterisk", "Item with dash", "Item with plus"]
    assert extract_bullet_points(content) == expected

    # List items with formatting
    content = dedent("""
        - **Bold item**
        - *Italic item*
        - `Code item`
        - [Link item](http://example.com)
        - Item with _multiple_ **formats** and `code`
        """)
    expected = [
        "**Bold item**",
        "*Italic item*",
        "`Code item`",
        "[Link item](http://example.com)",
        "Item with *multiple* **formats** and `code`",
    ]
    assert extract_bullet_points(content) == expected

    # Nested lists
    content = dedent("""
        - Top level item 1
          - Nested item 1.1
          - Nested item 1.2
        - Top level item 2
          1. Nested ordered 2.1
          2. Nested ordered 2.2
        """)
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
    content = dedent("""
        - First item that spans
          multiple lines with content
        - Second item
          that also spans multiple
          lines
        """)
    expected = [
        "First item that spans\nmultiple lines with content",
        "Second item\nthat also spans multiple\nlines",
    ]
    assert extract_bullet_points(content) == expected

    # Lists mixed with other content
    content = dedent("""
        # Header

        Some text before the list.

        - First item
        - Second item

        More text after the list.

        1. Another list item
        2. Final item

        Conclusion text.
        """)
    expected = ["First item", "Second item", "Another list item", "Final item"]
    assert extract_bullet_points(content) == expected

    # List items with complex content
    content = dedent("""
        - Item with **bold** and *italic* and `inline code`
        - Item with [external link](https://example.com) and [internal link](#section)
        - Item with line breaks
          and continued text
        """)
    expected = [
        "Item with **bold** and *italic* and `inline code`",
        "Item with [external link](https://example.com) and [internal link](#section)",
        "Item with line breaks\nand continued text",
    ]
    assert extract_bullet_points(content) == expected

    # Edge case: empty list items
    content = dedent("""
        - 
        - Non-empty item
        -   
        """)
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
    multiline_plain = dedent("""
        This is a paragraph
        with multiple lines
        and no bullets.""").strip()
    expected_multiline = ["This is a paragraph\nwith multiple lines\nand no bullets."]
    assert extract_bullet_points(multiline_plain) == expected_multiline
    try:
        extract_bullet_points(multiline_plain, strict=True)
        raise AssertionError("Expected ValueError for strict mode with no bullet points")
    except ValueError as e:
        assert "No bullet points found" in str(e)

    # Mixed content with no lists in strict mode
    mixed_no_lists = dedent("""
        # Header
        Some text here.
        **Bold text** and *italic*.
        """)
    try:
        extract_bullet_points(mixed_no_lists, strict=True)
        raise AssertionError("Expected ValueError for strict mode with no bullet points")
    except ValueError as e:
        assert "No bullet points found" in str(e)
    # Non-strict should return the content as single item
    assert len(extract_bullet_points(mixed_no_lists, strict=False)) == 1


def test_extract_bullet_points_key_scenarios() -> None:
    """Test key scenarios: plain text, multi-paragraph lists, and links in bullet text."""

    # Plain text handling (the fundamental case)
    plain_text = "This is just plain text without any markdown formatting."
    assert extract_bullet_points(plain_text) == [plain_text]

    # Multi-paragraph plain text
    multiline_plain = dedent("""
        This is a paragraph
        with multiple lines
        and no bullets at all.""").strip()
    assert extract_bullet_points(multiline_plain) == [multiline_plain]

    # Multi-paragraph bulleted lists with complex formatting
    multi_paragraph_content = dedent("""
        - First bullet point with **bold text** and a [link](https://example.com)
          
          This is a continuation paragraph within the same bullet point.
          It spans multiple lines and includes *italic text*.

        - Second bullet point with `inline code` and another [internal link](#section)
          
          Another paragraph here with more content.
          Including **bold** and *italic* formatting.

        - Third simple bullet
        """)
    expected_multi = [
        "First bullet point with **bold text** and a [link](https://example.com)\n\nThis is a continuation paragraph within the same bullet point.\nIt spans multiple lines and includes *italic text*.",
        "Second bullet point with `inline code` and another [internal link](#section)\n\nAnother paragraph here with more content.\nIncluding **bold** and *italic* formatting.",
        "Third simple bullet",
    ]
    result_multi = extract_bullet_points(multi_paragraph_content)
    assert result_multi == expected_multi

    # Links inside bullet text (various types)
    links_content = dedent("""
        - Check out [this external link](https://google.com) for more info
        - Visit [our docs](https://docs.example.com/api) and [FAQ](https://example.com/faq)
        - Internal reference: [see section below](#implementation)
        - Mixed: [external](https://test.com) and [internal](#ref) in one bullet
        - Email link: [contact us](mailto:test@example.com)
        - Link with **bold text**: [**Important Link**](https://critical.com)
        """)
    expected_links = [
        "Check out [this external link](https://google.com) for more info",
        "Visit [our docs](https://docs.example.com/api) and [FAQ](https://example.com/faq)",
        "Internal reference: [see section below](#implementation)",
        "Mixed: [external](https://test.com) and [internal](#ref) in one bullet",
        "Email link: [contact us](mailto:test@example.com)",
        "Link with **bold text**: [**Important Link**](https://critical.com)",
    ]
    result_links = extract_bullet_points(links_content)
    assert result_links == expected_links

    # Complex formatting combinations
    complex_content = dedent("""
        - **Bold** start with [link](https://example.com) and `code` end
        - *Italic* with `inline code` and [another link](https://test.com) here
        - Mixed: **bold _nested italic_** and `code with [link inside](https://nested.com)`
        """)
    expected_complex = [
        "**Bold** start with [link](https://example.com) and `code` end",
        "*Italic* with `inline code` and [another link](https://test.com) here",
        "Mixed: **bold *nested italic*** and `code with [link inside](https://nested.com)`",
    ]
    result_complex = extract_bullet_points(complex_content)
    assert result_complex == expected_complex


def test_markdown_structure_parsing() -> None:
    """Test that demonstrates how markdown structure is parsed and preserved."""

    # Test markdown structure preservation in list items
    content = dedent("""
        - First bullet with **bold text**

          This is a continuation paragraph with *italic text*.
          It spans multiple lines.

          Another paragraph in the same list item.

        - Second bullet with `code` and [link](https://example.com)
        """)

    result = extract_bullet_points(content)

    # Verify we get exactly 2 bullet points
    assert len(result) == 2

    # Verify first bullet preserves all formatting and paragraph structure
    expected_first = "First bullet with **bold text**\n\nThis is a continuation paragraph with *italic text*.\nIt spans multiple lines.\n\nAnother paragraph in the same list item."
    assert result[0] == expected_first

    # Verify second bullet preserves formatting
    expected_second = "Second bullet with `code` and [link](https://example.com)"
    assert result[1] == expected_second

    # Test nested formatting combinations
    nested_content = dedent("""
        - Item with **bold containing *italic* text** and `code`
        - Link with formatting: [**Bold Link Text**](https://example.com)
        - Code with special chars: `function(param="value")`
        """)

    nested_result = extract_bullet_points(nested_content)
    assert len(nested_result) == 3
    assert nested_result[0] == "Item with **bold containing *italic* text** and `code`"
    assert nested_result[1] == "Link with formatting: [**Bold Link Text**](https://example.com)"
    assert nested_result[2] == 'Code with special chars: `function(param="value")`'


def test_markdown_utils_exceptions() -> None:
    """Test exception handling for markdown utility functions."""
    import tempfile

    # Test extract_file_links with non-existent file
    result = extract_file_urls(Path("/non/existent/file.md"))
    assert result == []  # Should return empty list for any error

    # Test extract_file_links with empty file (should work fine)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
        tmp.write("")
        tmp_path = Path(tmp.name)

    try:
        result = extract_file_urls(tmp_path)
        assert result == []  # Empty file has no links
    finally:
        tmp_path.unlink()

    # Test with invalid markdown formatting (markdown is very permissive)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
        tmp.write("[incomplete link\n# Header\n- List item")
        tmp_path = Path(tmp.name)

    try:
        result = extract_file_urls(tmp_path)
        # Should still work - marko is very permissive with markdown
        assert isinstance(result, list)
    finally:
        tmp_path.unlink()

    # Test extract_links with string content
    content = "Check out [this link](https://example.com) and [internal](#section)"
    result = extract_urls(content)
    assert "https://example.com" in result
    assert "#section" not in result  # Internal links excluded by default

    result_with_internal = extract_urls(content, include_internal=True)
    assert "https://example.com" in result_with_internal
    assert "#section" in result_with_internal


def test_extract_links_comprehensive() -> None:
    """Test extract_links with various link formats including bare links and footnotes."""

    # Test regular markdown links
    regular_links = "Check out [this link](https://example.com) and [another](https://test.com)"
    result = extract_urls(regular_links)
    assert "https://example.com" in result
    assert "https://test.com" in result
    assert len(result) == 2

    # Test bare/autolinks in angle brackets
    bare_links = "Visit <https://google.com> and also <https://github.com>"
    result_bare = extract_urls(bare_links)
    assert "https://google.com" in result_bare
    assert "https://github.com" in result_bare
    assert len(result_bare) == 2

    # Test autolinks without brackets (GFM extension enables auto-linking of plain URLs)
    auto_links = "Visit https://stackoverflow.com or http://reddit.com"
    result_auto = extract_urls(auto_links)
    assert "https://stackoverflow.com" in result_auto
    assert "http://reddit.com" in result_auto
    assert len(result_auto) == 2  # GFM auto-links plain URLs

    # Test GFM footnotes (the original issue)
    footnote_content = """
[^109]: What Is The Future Of Ketamine Therapy For Mental Health Treatment?
    - The Ko-Op, accessed June 28, 2025,
      <https://psychedelictherapists.co/blog/the-future-of-ketamine-assisted-psychotherapy/>
"""
    result_footnote = extract_urls(footnote_content)
    assert (
        "https://psychedelictherapists.co/blog/the-future-of-ketamine-assisted-psychotherapy/"
        in result_footnote
    )
    assert len(result_footnote) == 1

    # Test mixed content with all types (excluding reference-style which has parsing conflicts with footnotes)
    mixed_content = """
# Header

Regular link: [Example](https://example.com)
Bare link: <https://bare-link.com>
Auto link: https://auto-link.com

[^1]: Footnote with [regular link](https://footnote-regular.com)
[^2]: Footnote with bare link <https://footnote-bare.com>
"""
    result_mixed = extract_urls(mixed_content)
    expected_links = [
        "https://example.com",  # Regular link
        "https://bare-link.com",  # Bare link
        "https://auto-link.com",  # Plain auto link (GFM extension)
        "https://footnote-regular.com",  # Link in footnote
        "https://footnote-bare.com",  # Bare link in footnote
    ]
    for link in expected_links:
        assert link in result_mixed, f"Missing expected link: {link}"
    assert len(result_mixed) == len(expected_links)


def test_extract_bare_links() -> None:
    """Test extraction of bare links in angle brackets."""
    content = "Visit <https://example.com> and <https://github.com/user/repo> for more info"
    result = extract_urls(content)
    assert "https://example.com" in result
    assert "https://github.com/user/repo" in result
    assert len(result) == 2


def test_extract_footnote_links() -> None:
    """Test extraction of links within footnotes."""
    content = dedent("""
        Main text with reference[^1].
        
        [^1]: This footnote has a [regular link](https://example.com) and <https://bare-link.com>
        """)
    result = extract_urls(content)
    assert "https://example.com" in result
    assert "https://bare-link.com" in result
    assert len(result) == 2


def test_extract_reference_style_links() -> None:
    """Test extraction of reference-style links."""
    content = dedent("""
        Check out [this article][ref1] and [this other one][ref2].
        
        [ref1]: https://example.com/article1
        [ref2]: https://example.com/article2
        """)
    result = extract_urls(content)
    assert "https://example.com/article1" in result
    assert "https://example.com/article2" in result
    assert len(result) == 2


def test_extract_links_and_dups() -> None:
    """Test that internal fragment links are excluded by default but included when requested."""
    content = dedent("""
        See [this section](#introduction) and [external link](https://example.com).
        Also check [another section](#conclusion) here.
        Adding a [duplicate](https://example.com).
        """)

    # Default behavior: exclude internal links
    result = extract_urls(content)
    assert "https://example.com" in result
    assert "#introduction" not in result
    assert "#conclusion" not in result
    assert len(result) == 1

    # Include internal links
    result_with_internal = extract_urls(content, include_internal=True)
    assert "https://example.com" in result_with_internal
    assert "#introduction" in result_with_internal
    assert "#conclusion" in result_with_internal
    assert len(result_with_internal) == 3


def test_extract_links_mixed_real_world() -> None:
    """Test with a realistic mixed document containing various link types."""
    content = dedent("""
        # Research Article
        
        This study examines ketamine therapy[^109] and references multiple sources.
        
        ## Methods
        
        We reviewed literature from [PubMed](https://pubmed.ncbi.nlm.nih.gov) 
        and other databases <https://scholar.google.com>.
        
        For protocol details, see [our methodology][methodology].
        
        [methodology]: https://research.example.com/protocol
        
        [^109]: What Is The Future Of Ketamine Therapy For Mental Health Treatment?
            - The Ko-Op, accessed June 28, 2025,
              <https://psychedelictherapists.co/blog/the-future-of-ketamine-assisted-psychotherapy/>
        """)

    result = extract_urls(content)
    expected_links = [
        "https://pubmed.ncbi.nlm.nih.gov",
        "https://scholar.google.com",
        "https://research.example.com/protocol",
        "https://psychedelictherapists.co/blog/the-future-of-ketamine-assisted-psychotherapy/",
    ]

    for link in expected_links:
        assert link in result, f"Missing expected link: {link}"
    assert len(result) == len(expected_links)


def test_rewrite_image_paths() -> None:
    """Test rewriting image paths in markdown content."""

    # Test content with various image types
    content = dedent("""
        # Document with Images
        
        Here's a local image: ![Alt text](./images/local.png)
        
        And a remote image: ![Remote](https://example.com/remote.jpg)
        
        Another local one: ![Another](../assets/photo.jpeg "Title")
        
        More content here.
        """)

    # Test rewriting ./images/ prefix (default include_img_tags=True)
    result1 = rewrite_image_urls(content, "./images/", "./new-images/")
    assert "./new-images/local.png" in result1
    assert "./images/local.png" not in result1
    assert "https://example.com/remote.jpg" in result1  # Remote unchanged
    assert "../assets/photo.jpeg" in result1  # Other local unchanged

    # Test rewriting ../assets/ prefix
    result2 = rewrite_image_urls(content, "../assets/", "./new-assets/")
    assert "./new-assets/photo.jpeg" in result2
    assert "../assets/photo.jpeg" not in result2
    assert "./images/local.png" in result2  # Other local unchanged
    assert "https://example.com/remote.jpg" in result2  # Remote unchanged

    # Test rewriting remote URLs
    result3 = rewrite_image_urls(content, "https://example.com/", "https://cdn.example.com/")
    assert "https://cdn.example.com/remote.jpg" in result3
    assert "https://example.com/remote.jpg" not in result3
    assert "./images/local.png" in result3  # Local unchanged
    assert "../assets/photo.jpeg" in result3  # Local unchanged


def test_rewrite_image_paths_no_images() -> None:
    """Test rewriting on content with no images."""
    content = dedent("""
        # No Images Here
        
        Just some regular text and [a link](https://example.com).
        
        And a list:
        - Item 1
        - Item 2
        """)

    result = rewrite_image_urls(content, "./", "rewritten-")

    # Content should be essentially unchanged (except possible minor formatting)
    assert "# No Images Here" in result
    assert "[a link](https://example.com)" in result
    assert "- Item 1" in result


def test_rewrite_image_paths_only_remote() -> None:
    """Test rewriting on content with only remote images."""
    content = dedent("""
        # Remote Images Only
        
        ![Image 1](https://example.com/image1.png)
        ![Image 2](http://test.com/image2.jpg)
        """)

    # Test rewriting https:// prefix
    result1 = rewrite_image_urls(content, "https://example.com/", "https://cdn.example.com/")
    assert "https://cdn.example.com/image1.png" in result1
    assert "https://example.com/image1.png" not in result1
    assert "http://test.com/image2.jpg" in result1  # Other protocol unchanged

    # Test rewriting http:// prefix
    result2 = rewrite_image_urls(content, "http://test.com/", "https://secure.test.com/")
    assert "https://secure.test.com/image2.jpg" in result2
    assert "http://test.com/image2.jpg" not in result2
    assert "https://example.com/image1.png" in result2  # Other URL unchanged


def test_rewrite_image_paths_complex() -> None:
    """Test rewriting with complex markdown structure."""
    content = dedent("""
        # Main Title
        
        ## Section with Images
        
        Here's an image in a paragraph: ![Local](./local.png)
        
        > This is a blockquote with an image: ![Quote image](images/quote.jpg)
        
        1. List item with image: ![List image](./list.png)
        2. Another item
        
        | Table | With |
        |-------|------|
        | ![Table image](table.png) | Cell |
        
        And a remote one: ![Remote](https://remote.com/image.png)
        """)

    # Test rewriting relative paths with ./ prefix
    result1 = rewrite_image_urls(content, "./", "assets/")
    assert "assets/local.png" in result1
    assert "assets/list.png" in result1
    assert "./local.png" not in result1
    assert "./list.png" not in result1
    assert "images/quote.jpg" in result1  # No ./ prefix, unchanged
    assert "table.png" in result1  # No ./ prefix, unchanged
    assert "https://remote.com/image.png" in result1  # Remote unchanged

    # Test rewriting paths without prefix
    result2 = rewrite_image_urls(content, "images/", "new-images/")
    assert "new-images/quote.jpg" in result2
    assert "![Quote image](images/quote.jpg)" not in result2  # Check full image syntax
    assert "./local.png" in result2  # Different prefix, unchanged

    # Test rewriting absolute URLs
    result3 = rewrite_image_urls(content, "https://remote.com/", "https://cdn.remote.com/")
    assert "https://cdn.remote.com/image.png" in result3
    assert "https://remote.com/image.png" not in result3


def test_rewrite_urls_all_types() -> None:
    """Test the generalized URL rewriter with all element types."""
    content = dedent("""
        # Document with Various URL Types
        
        Regular link: [Example](https://example.com/page)
        
        Auto link: <https://autolink.com>  
        
        Image: ![Alt text](./image.png)
        
        Reference link: [Ref link][ref]
        
        [ref]: https://reference.com/target
        """)

    def add_prefix(url: str) -> str | None:
        if url.startswith("https://example.com"):
            return url.replace("https://example.com", "https://newsite.com")
        elif url.startswith("./"):
            return f"assets/{url[2:]}"
        return None  # Skip other URLs

    result = rewrite_urls(content, add_prefix)

    # Check rewritten URLs
    assert "https://newsite.com/page" in result
    assert "assets/image.png" in result

    # Check unchanged URLs
    assert "https://autolink.com" in result
    assert "https://reference.com/target" in result


def test_rewrite_urls_element_type_filter() -> None:
    """Test filtering by element type."""
    content = dedent("""
        # Links and Images
        
        Link: [Example](./local-link.html)
        Image: ![Alt](./local-image.png)
        Auto: <./auto-link.html>
        """)

    def prefix_local(url: str) -> str | None:
        if url.startswith("./"):
            return f"new/{url[2:]}"
        return None

    # Only rewrite images
    result_images = rewrite_urls(content, prefix_local, element_types=(Image,))
    assert "new/local-image.png" in result_images
    assert "./local-link.html" in result_images  # Link unchanged
    assert "./auto-link.html" in result_images  # AutoLink unchanged

    # Only rewrite regular links
    result_links = rewrite_urls(content, prefix_local, element_types=(Link,))
    assert "new/local-link.html" in result_links
    assert "./local-image.png" in result_links  # Image unchanged
    assert "./auto-link.html" in result_links  # AutoLink unchanged

    # Rewrite both links and images
    result_both = rewrite_urls(content, prefix_local, element_types=(Link, Image))
    assert "new/local-link.html" in result_both
    assert "new/local-image.png" in result_both
    assert "./auto-link.html" in result_both  # AutoLink unchanged


def test_rewrite_urls_unified_filter() -> None:
    """Test unified filtering and rewriting in the rewriter function."""
    content = dedent("""
        # Mixed Local and Remote
        
        Local link: [Local](./local.html)
        Remote link: [Remote](https://example.com/remote.html)
        Local image: ![Local](./image.png) 
        Remote image: ![Remote](https://example.com/image.jpg)
        """)

    def make_absolute_if_local(url: str) -> str | None:
        # Only rewrite local URLs, skip remote ones
        if url.startswith("./"):
            return f"https://mysite.com/{url[2:]}"
        return None  # Skip remote URLs

    result = rewrite_urls(content, make_absolute_if_local)

    # Local URLs should be rewritten
    assert "https://mysite.com/local.html" in result
    assert "https://mysite.com/image.png" in result

    # Remote URLs should be unchanged
    assert "https://example.com/remote.html" in result
    assert "https://example.com/image.jpg" in result


def test_rewrite_urls_none_return() -> None:
    """Test that returning None skips rewriting."""
    content = dedent("""
        # Test Selective Rewriting
        
        Keep this: [Keep](./keep.html)
        Change this: [Change](./change.html)
        """)

    def selective_rewriter(url: str) -> str | None:
        if "change" in url:
            return url.replace("./change.html", "./modified.html")
        return None  # Skip everything else

    result = rewrite_urls(content, selective_rewriter)

    assert "./modified.html" in result
    assert "./keep.html" in result  # Unchanged


def test_rewrite_urls_reference_links() -> None:
    """Test rewriting reference link definitions."""
    content = dedent("""
        # Reference Links
        
        Here's a [reference link][ref1] and [another][ref2].
        
        [ref1]: ./local-ref.html "Local Reference"
        [ref2]: https://example.com/remote-ref.html "Remote Reference"  
        """)

    def update_local_refs(url: str) -> str | None:
        if url.startswith("./"):
            return url.replace("./", "./updated/")
        return None

    result = rewrite_urls(content, update_local_refs, element_types=(LinkRefDef,))

    # Reference definition should be updated
    assert "./updated/local-ref.html" in result

    # Remote reference should be unchanged
    assert "https://example.com/remote-ref.html" in result


def test_rewrite_urls_complex_scenario() -> None:
    """Test complex scenario with multiple filters and rewriters."""
    content = dedent("""
        # Complex Document
        
        ## Links Section
        - [Internal page](./pages/about.html)
        - [External site](https://external.com)
        - <./contact.html>
        
        ## Images Section  
        ![Logo](./assets/logo.png)
        ![External](https://cdn.example.com/image.jpg)
        
        ## References
        [About page][about]
        [Contact][contact]
        
        [about]: ./pages/about.html
        [contact]: ./contact.html
        """)

    def comprehensive_rewriter(url: str) -> str | None:
        # Move local pages to new structure
        if url.startswith("./pages/"):
            return url.replace("./pages/", "./new-pages/")
        # Move assets to CDN
        elif url.startswith("./assets/"):
            return url.replace("./assets/", "https://cdn.mysite.com/")
        # Update contact page
        elif url == "./contact.html":
            return "./new-contact.html"
        return None

    result = rewrite_urls(content, comprehensive_rewriter)

    # Check all expected rewrites
    assert "./new-pages/about.html" in result
    assert "https://cdn.mysite.com/logo.png" in result
    assert "./new-contact.html" in result

    # Check unchanged URLs
    assert "https://external.com" in result
    assert "https://cdn.example.com/image.jpg" in result


def test_rewrite_urls_simplified_api() -> None:
    """Test the simplified unified API with various rewriting scenarios."""
    content = dedent("""
        # Website Migration
        
        ## Local Content
        - [About](./about.html)
        - [Help](./help/faq.html)
        - ![Logo](./images/logo.png)
        - <./contact.html>
        
        ## External Content  
        - [Partner](https://partner.com)
        - ![CDN Image](https://cdn.example.com/img.jpg)
        - <https://external-service.com>
        
        ## Reference Links
        [Privacy Policy][privacy]
        [Terms][terms]
        
        [privacy]: ./legal/privacy.html
        [terms]: https://example.com/terms
        """)

    def migration_rewriter(url: str) -> str | None:
        """
        Unified rewriter that handles both filtering and rewriting:
        - Migrates local pages to new site structure
        - Moves images to CDN
        - Updates specific domains
        - Skips other URLs unchanged
        """
        # Local HTML pages -> new site structure
        if url.startswith("./") and url.endswith(".html"):
            if "/help/" in url:
                # Move help pages to support section
                filename = url.split("/")[-1]
                return f"https://newsite.com/support/{filename}"
            elif "/legal/" in url:
                # Move legal pages to main site
                filename = url.split("/")[-1]
                return f"https://newsite.com/legal/{filename}"
            else:
                # Root level pages
                filename = url[2:]  # Remove "./"
                return f"https://newsite.com/{filename}"

        # Local images -> CDN
        elif url.startswith("./images/"):
            filename = url.split("/")[-1]
            return f"https://cdn.newsite.com/{filename}"

        # Domain migration for external links
        elif url.startswith("https://example.com"):
            return url.replace("example.com", "newsite.com")

        # Skip all other URLs (external services, CDNs, etc.)
        return None

    result = rewrite_urls(content, migration_rewriter)

    # Verify local page migrations
    assert "https://newsite.com/about.html" in result
    assert "https://newsite.com/support/faq.html" in result
    assert "https://newsite.com/legal/privacy.html" in result

    # Verify image migration to CDN
    assert "https://cdn.newsite.com/logo.png" in result

    # Verify domain migration
    assert "https://newsite.com/terms" in result

    # Verify unchanged external URLs
    assert "https://partner.com" in result
    assert "https://cdn.example.com/img.jpg" in result
    assert "https://external-service.com" in result

    # Verify that relative URLs in angle brackets remain unchanged
    # (marko doesn't parse them as URL elements)
    assert "<./contact.html>" in result


def test_extract_links_parentheses_adjacent() -> None:
    """URLs adjacent to closing parentheses should not include the parenthesis."""
    content = dedent(
        """
        [^res1]: Under 50 U.S.C. § 4531(c)(3), amounts in the Defense Production Act Fund (used
            for Title III) “shall remain available until expended,” meaning they do not expire
            at the end of a fiscal year (law text:
            https://www.law.cornell.edu/uscode/text/50/4531).

        [^res2]: USAspending.gov’s federal account 097-0801 (Defense Production Act Purchases,
            Defense) provides official figures for obligations and unobligated balances by
            fiscal year drawn from Treasury data (https://www.usaspending.gov/account/097-0801).
        """
    )

    links = extract_urls(content)
    assert "https://www.law.cornell.edu/uscode/text/50/4531" in links
    assert "https://www.law.cornell.edu/uscode/text/50/4531)" not in links

    assert "https://www.usaspending.gov/account/097-0801" in links
    assert "https://www.usaspending.gov/account/097-0801)" not in links
