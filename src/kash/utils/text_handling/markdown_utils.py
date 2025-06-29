import re
from pathlib import Path
from textwrap import dedent
from typing import Any, TypeAlias

import marko
import regex
from marko.block import Heading, ListItem
from marko.inline import AutoLink, Link

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
            case AutoLink():
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


def extract_bullet_points(content: str, *, strict: bool = False) -> list[str]:
    """
    Extract list item values from a Markdown file, preserving all original formatting.

    If no bullet points are found and `strict` is False, returns the entire content
    as a single item (treating plain text as if it were the first bullet point).
    If `strict` is True, only actual list items are returned.

    Raises:
        ValueError: If `strict` is True and no bullet points are found.
        marko.ParseError: If the markdown content contains invalid syntax that cannot be parsed.
    """
    document = marko.parse(content)
    bullet_points: list[str] = []

    def _find_bullet_points(element):
        if isinstance(element, ListItem):
            # Extract markdown from this list item, preserving formatting
            bullet_points.append(_extract_list_item_markdown(element).strip())
            # Then recursively process any nested lists within this item
            if hasattr(element, "children"):
                for child in element.children:
                    _find_bullet_points(child)
        elif hasattr(element, "children"):
            for child in element.children:
                _find_bullet_points(child)

    _find_bullet_points(document)

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


def test_extract_links_comprehensive() -> None:
    """Test extract_links with various link formats including bare links and footnotes."""

    # Test regular markdown links
    regular_links = "Check out [this link](https://example.com) and [another](https://test.com)"
    result = extract_links(regular_links)
    assert "https://example.com" in result
    assert "https://test.com" in result
    assert len(result) == 2

    # Test bare/autolinks in angle brackets
    bare_links = "Visit <https://google.com> and also <https://github.com>"
    result_bare = extract_links(bare_links)
    assert "https://google.com" in result_bare
    assert "https://github.com" in result_bare
    assert len(result_bare) == 2

    # Test autolinks without brackets (expected to not work with standard markdown)
    auto_links = "Visit https://stackoverflow.com or http://reddit.com"
    result_auto = extract_links(auto_links)
    assert (
        result_auto == []
    )  # Plain URLs without brackets aren't parsed as links in standard markdown

    # Test GFM footnotes (the original issue)
    footnote_content = """
[^109]: What Is The Future Of Ketamine Therapy For Mental Health Treatment?
    - The Ko-Op, accessed June 28, 2025,
      <https://psychedelictherapists.co/blog/the-future-of-ketamine-assisted-psychotherapy/>
"""
    result_footnote = extract_links(footnote_content)
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
    result_mixed = extract_links(mixed_content)
    expected_links = [
        "https://example.com",  # Regular link
        "https://bare-link.com",  # Bare link
        "https://footnote-regular.com",  # Link in footnote
        "https://footnote-bare.com",  # Bare link in footnote
    ]
    for link in expected_links:
        assert link in result_mixed, f"Missing expected link: {link}"
    # Should not include plain auto link (https://auto-link.com) as it's not in angle brackets
    assert "https://auto-link.com" not in result_mixed
    assert len(result_mixed) == len(expected_links)


def test_extract_bare_links() -> None:
    """Test extraction of bare links in angle brackets."""
    content = "Visit <https://example.com> and <https://github.com/user/repo> for more info"
    result = extract_links(content)
    assert "https://example.com" in result
    assert "https://github.com/user/repo" in result
    assert len(result) == 2


def test_extract_footnote_links() -> None:
    """Test extraction of links within footnotes."""
    content = dedent("""
        Main text with reference[^1].
        
        [^1]: This footnote has a [regular link](https://example.com) and <https://bare-link.com>
        """)
    result = extract_links(content)
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
    result = extract_links(content)
    assert "https://example.com/article1" in result
    assert "https://example.com/article2" in result
    assert len(result) == 2


def test_extract_links_with_internal_fragments() -> None:
    """Test that internal fragment links are excluded by default but included when requested."""
    content = dedent("""
        See [this section](#introduction) and [external link](https://example.com).
        Also check [another section](#conclusion) here.
        """)

    # Default behavior: exclude internal links
    result = extract_links(content)
    assert "https://example.com" in result
    assert "#introduction" not in result
    assert "#conclusion" not in result
    assert len(result) == 1

    # Include internal links
    result_with_internal = extract_links(content, include_internal=True)
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

    result = extract_links(content)
    expected_links = [
        "https://pubmed.ncbi.nlm.nih.gov",
        "https://scholar.google.com",
        "https://research.example.com/protocol",
        "https://psychedelictherapists.co/blog/the-future-of-ketamine-assisted-psychotherapy/",
    ]

    for link in expected_links:
        assert link in result, f"Missing expected link: {link}"
    assert len(result) == len(expected_links)
