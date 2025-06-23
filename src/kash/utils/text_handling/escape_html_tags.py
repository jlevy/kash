import re
from collections.abc import Set

HTML_IN_MD_TAGS = frozenset(["div", "span", "sup", "sub", "br", "details", "summary"])
"""These are tags that have reasonable usage in Markdown so typically would be preserved."""

ALLOWED_BARE_PROTOS = frozenset(["http://", "https://", "file://"])


def escape_html_tags(
    html_content: str,
    whitelist_tags: Set[str] = HTML_IN_MD_TAGS,
    allow_bare_md_urls: bool = False,
) -> str:
    """
    Escapes HTML tags by replacing '<' with '&lt;', except for whitelisted tags and
    markdown-style URLs like <https://example.com>. Whitelist defaults to the only a
    few common tags. But it can also be empty to escape all tags.
    """
    result = []
    last_pos = 0

    # Compile patterns for matching at each '<' position
    # Match <, optional spaces, optional /, optional spaces, whitelisted tag, then optional attributes, then optional /, optional spaces, then >
    whitelist_pattern = re.compile(
        r"< *(/?) *(" + "|".join(whitelist_tags) + r")(?:\s+[^>]*)? *(/?) *>",
        re.IGNORECASE,
    )

    url_pattern = None
    if allow_bare_md_urls:
        url_pattern = re.compile(
            r"<(?:" + "|".join(re.escape(proto) for proto in ALLOWED_BARE_PROTOS) + r")[^>\s]+>"
        )

    # Find all '<' characters
    for match in re.finditer(r"<", html_content):
        start_pos = match.start()

        # Add text before this '<'
        result.append(html_content[last_pos:start_pos])

        # Try to match patterns at this position
        substring = html_content[start_pos:]
        whitelist_match = whitelist_pattern.match(substring)
        url_match = url_pattern and url_pattern.match(substring)

        if whitelist_match:
            result.append(whitelist_match.group(0))
            last_pos = start_pos + len(whitelist_match.group(0))
        elif url_match:
            result.append(url_match.group(0))
            last_pos = start_pos + len(url_match.group(0))
        else:
            # No match, escape this '<'
            result.append("&lt;")
            last_pos = start_pos + 1

    # Add remaining text
    result.append(html_content[last_pos:])

    return "".join(result)


## Tests


def test_escape_html_tags():
    """Tests the escape_html_tags function with various cases."""

    # Basic Whitelist Check (Default)
    assert escape_html_tags("<div>Test</div>") == "<div>Test</div>"
    assert escape_html_tags("<span>Test</span>") == "<span>Test</span>"
    assert escape_html_tags("<br>") == "<br>"
    assert (
        escape_html_tags("<details><summary>Sum</summary>Det</details>")
        == "<details><summary>Sum</summary>Det</details>"
    )

    # Basic Escape Check
    assert escape_html_tags("<p>Test</p>") == "&lt;p>Test&lt;/p>"
    assert escape_html_tags("<script>alert('x');</script>") == "&lt;script>alert('x');&lt;/script>"
    assert escape_html_tags("<img>") == "&lt;img>"

    # Case Insensitivity
    assert escape_html_tags("<DiV>Case</DiV>") == "<DiV>Case</DiV>"  # Whitelisted
    assert escape_html_tags("<P>Test</P>") == "&lt;P>Test&lt;/P>"  # Escaped

    # Self-closing tags
    assert escape_html_tags("<br/>") == "<br/>"  # Whitelisted
    assert escape_html_tags("<br />") == "<br />"  # Whitelisted
    assert escape_html_tags("<img/>") == "&lt;img/>"  # Escaped

    # Tags with Attributes
    assert (
        escape_html_tags('<div class="foo">Test</div>') == '<div class="foo">Test</div>'
    )  # Whitelisted
    assert (
        escape_html_tags('<span id="bar" data-val="x">Test</span>')
        == '<span id="bar" data-val="x">Test</span>'
    )  # Whitelisted
    assert escape_html_tags('<p class="foo">Test</p>') == '&lt;p class="foo">Test&lt;/p>'  # Escaped
    assert escape_html_tags('<img src="a.jpg"/>') == '&lt;img src="a.jpg"/>'  # Escaped

    # Markdown URL Handling
    url_md = "Check <https://example.com> and <http://test.org/path>"
    assert escape_html_tags(url_md, allow_bare_md_urls=True) == url_md
    assert (
        escape_html_tags(url_md, allow_bare_md_urls=False)
        == "Check &lt;https://example.com> and &lt;http://test.org/path>"
    )

    url_mixed = "<div>Link: <https://ok.com></div> <script>no</script>"
    expected_mixed_urls_allowed = "<div>Link: <https://ok.com></div> &lt;script>no&lt;/script>"
    expected_mixed_urls_disallowed = (
        "<div>Link: &lt;https://ok.com></div> &lt;script>no&lt;/script>"
    )
    assert escape_html_tags(url_mixed, allow_bare_md_urls=True) == expected_mixed_urls_allowed
    assert escape_html_tags(url_mixed, allow_bare_md_urls=False) == expected_mixed_urls_disallowed

    assert (
        escape_html_tags("<http://malformed url>", allow_bare_md_urls=True)
        == "&lt;http://malformed url>"
    )
    assert (
        escape_html_tags("</https://example.com>", allow_bare_md_urls=True)
        == "&lt;/https://example.com>"
    )  # Closing URL-like is escaped

    # Nested/Malformed '<' and Edge Cases
    assert escape_html_tags("<<script>>") == "&lt;&lt;script>>"  # Escaped non-tag <
    assert escape_html_tags("<div><p>nested</p></div>") == "<div>&lt;p>nested&lt;/p></div>"
    assert escape_html_tags("<div<span") == "&lt;div&lt;span"  # Incomplete tags are escaped
    assert (
        escape_html_tags("Text < with > inside") == "Text &lt; with > inside"
    )  # Escape < even if > exists later
    assert escape_html_tags("<") == "&lt;"
    assert escape_html_tags(">") == ">"
    assert escape_html_tags("<>") == "&lt;>"
    assert escape_html_tags("< >") == "&lt; >"
    assert escape_html_tags("< / div >") == "< / div >"  # Whitelisted closing tag with spaces

    # Mixed Content Combination
    complex_html = "<DiV class='A'>Hello <Br/> <p>World</p> <https://link.com> </DiV>"
    expected_complex_allowed = (
        "<DiV class='A'>Hello <Br/> &lt;p>World&lt;/p> <https://link.com> </DiV>"
    )
    expected_complex_disallowed = (
        "<DiV class='A'>Hello <Br/> &lt;p>World&lt;/p> &lt;https://link.com> </DiV>"
    )
    assert escape_html_tags(complex_html, allow_bare_md_urls=True) == expected_complex_allowed
    assert escape_html_tags(complex_html, allow_bare_md_urls=False) == expected_complex_disallowed

    # Empty/No Tags
    assert escape_html_tags("") == ""
    assert escape_html_tags("Just plain text, no tags.") == "Just plain text, no tags."
